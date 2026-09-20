from dataclasses import dataclass
from typing import Protocol, TypeVar


@dataclass(frozen=True, slots=True, kw_only=True)
class Command:
  pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TransactionalCommand(Command):
  pass


@dataclass(frozen=True, slots=True, kw_only=True)
class Query:
  pass


RequestT_contra = TypeVar(
  "RequestT_contra",
  bound=Command | Query,
  contravariant=True,
)
ResultT_co = TypeVar("ResultT_co", covariant=True)


class Handler(Protocol[RequestT_contra, ResultT_co]):
  def handle(self, request: RequestT_contra) -> ResultT_co:
    ...
