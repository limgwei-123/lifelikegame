from collections.abc import Callable, Iterable
from typing import Any, cast

from app.core.behaviors import Behavior
from app.core.cqrs import Command, Handler, Query, RequestT_contra, ResultT_co


class DuplicateHandlerError(RuntimeError):
  pass


class HandlerNotFoundError(LookupError):
  pass


class HandlerRegistry:
  def __init__(self) -> None:
    self._handlers: dict[type[Command | Query], Handler[Any, Any]] = {}

  def register(
      self,
      request_type: type[RequestT_contra],
      handler: Handler[RequestT_contra, ResultT_co],
  ) -> None:
    if request_type in self._handlers:
      raise DuplicateHandlerError(
        f"Handler already registered for {request_type.__name__}"
      )

    self._handlers[request_type] = handler

  def resolve(
      self,
      request_type: type[RequestT_contra],
  ) -> Handler[RequestT_contra, Any]:
    handler = self._handlers.get(request_type)
    if handler is None:
      raise HandlerNotFoundError(
        f"Handler not found for {request_type.__name__}"
      )

    return cast(Handler[RequestT_contra, Any], handler)


class Mediator:
  def __init__(
      self,
      registry: HandlerRegistry,
      behaviors: Iterable[Behavior[Any, Any]] = (),
  ):
    self._registry = registry
    self._behaviors = tuple(behaviors)

  def send(self, request: RequestT_contra) -> Any:
    handler = self._registry.resolve(type(request))
    next_handler: Callable[[], Any] = lambda: handler.handle(request)

    def wrap(
        behavior: Behavior[Any, Any],
        next_step: Callable[[], Any],
    ) -> Callable[[], Any]:
      return lambda: behavior.handle(request, next_step)

    for behavior in reversed(self._behaviors):
      next_handler = wrap(behavior, next_handler)

    return next_handler()
