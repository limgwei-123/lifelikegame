from collections.abc import Callable, Iterable
from contextvars import ContextVar, Token
from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Any, Protocol, TypeVar
from uuid import uuid4

from app.core.cqrs import Command, Handler, Query, TransactionalCommand
from app.core.unit_of_work import UnitOfWork
from app.errors.exception import RequestValidationError


BehaviorResultT = TypeVar("BehaviorResultT")
ValidationRequestT_contra = TypeVar(
  "ValidationRequestT_contra",
  bound=Command | Query,
  contravariant=True,
)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


@dataclass(frozen=True, slots=True)
class BehaviorContext:
  request: Command | Query
  handler: Handler[Any, Any]


def bind_request_id(request_id: str) -> Token[str | None]:
  return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
  _request_id.reset(token)


def get_request_id() -> str | None:
  return _request_id.get()


class Behavior(Protocol[BehaviorResultT]):
  def handle(
      self,
      context: BehaviorContext,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    ...


@dataclass(frozen=True, slots=True)
class ValidationIssue:
  field: str
  message: str
  code: str = "invalid"

  def to_dict(self) -> dict[str, str]:
    return {
      "field": self.field,
      "message": self.message,
      "code": self.code,
    }


class Validator(Protocol[ValidationRequestT_contra]):
  def validate(
      self,
      request: ValidationRequestT_contra,
  ) -> Iterable[ValidationIssue]:
    ...


class ValidatorRegistry:
  def __init__(self) -> None:
    self._validators: dict[
      type[Command | Query],
      list[Validator[Any]],
    ] = {}

  def register(
      self,
      request_type: type[ValidationRequestT_contra],
      validator: Validator[ValidationRequestT_contra],
  ) -> None:
    self._validators.setdefault(request_type, []).append(validator)

  def resolve(
      self,
      request_type: type[ValidationRequestT_contra],
  ) -> tuple[Validator[ValidationRequestT_contra], ...]:
    validators = self._validators.get(request_type, [])
    return tuple(validators)


class ValidationBehavior:
  def __init__(self, registry: ValidatorRegistry):
    self._registry = registry

  def handle(
      self,
      context: BehaviorContext,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    validators = self._registry.resolve(type(context.request))
    issues = [
      issue
      for validator in validators
      for issue in validator.validate(context.request)
    ]

    if issues:
      raise RequestValidationError([
        issue.to_dict()
        for issue in issues
      ])

    return next_handler()


class TransactionBehavior:
  def __init__(self, unit_of_work: UnitOfWork):
    self._unit_of_work = unit_of_work

  def handle(
      self,
      context: BehaviorContext,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    if not isinstance(context.request, TransactionalCommand):
      return next_handler()

    with self._unit_of_work.begin():
      return next_handler()


class LoggingBehavior:
  def __init__(self, logger: logging.Logger | None = None):
    self._logger = logger or logging.getLogger("app.cqrs")

  def handle(
      self,
      context: BehaviorContext,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    request_id = get_request_id()
    request_id_token = None
    if request_id is None:
      request_id = str(uuid4())
      request_id_token = bind_request_id(request_id)

    started_at = perf_counter()
    log_context = {
      "request_id": request_id,
      "request_type": type(context.request).__name__,
      "handler_type": type(context.handler).__name__,
      "transactional": isinstance(context.request, TransactionalCommand),
    }

    try:
      result = next_handler()
    except Exception:
      self._logger.exception(
        "cqrs_request_failed",
        extra={
          **log_context,
          "duration_ms": round((perf_counter() - started_at) * 1000, 3),
          "outcome": "failure",
        },
      )
      raise
    else:
      self._logger.info(
        "cqrs_request_completed",
        extra={
          **log_context,
          "duration_ms": round((perf_counter() - started_at) * 1000, 3),
          "outcome": "success",
        },
      )
      return result
    finally:
      if request_id_token is not None:
        reset_request_id(request_id_token)
