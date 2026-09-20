from collections.abc import Callable
from typing import Protocol, TypeVar

from app.core.cqrs import Command, Query, TransactionalCommand
from app.core.unit_of_work import UnitOfWork


BehaviorRequestT_contra = TypeVar(
  "BehaviorRequestT_contra",
  bound=Command | Query,
  contravariant=True,
)
BehaviorResultT = TypeVar("BehaviorResultT")


class Behavior(Protocol[BehaviorRequestT_contra, BehaviorResultT]):
  def handle(
      self,
      request: BehaviorRequestT_contra,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    ...


class TransactionBehavior:
  def __init__(self, unit_of_work: UnitOfWork):
    self._unit_of_work = unit_of_work

  def handle(
      self,
      request: Command | Query,
      next_handler: Callable[[], BehaviorResultT],
  ) -> BehaviorResultT:
    if not isinstance(request, TransactionalCommand):
      return next_handler()

    with self._unit_of_work.begin():
      return next_handler()
