from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session


class UnitOfWork:
  def __init__(self, session: Session):
    self.session = session
    self._is_active = False

  def begin(self) -> Self:
    return self

  def __enter__(self) -> Self:
    if self._is_active:
      raise RuntimeError("UnitOfWork transaction is already active")

    self._is_active = True
    return self

  def __exit__(
      self,
      exc_type: type[BaseException] | None,
      exc_value: BaseException | None,
      traceback: TracebackType | None,
  ) -> bool:
    try:
      if exc_type is not None:
        self.rollback()
        return False

      try:
        self.commit()
      except Exception:
        self.rollback()
        raise

      return False
    finally:
      self._is_active = False

  def commit(self) -> None:
    self.session.commit()

  def rollback(self) -> None:
    self.session.rollback()


def build_unit_of_work(session: Session) -> UnitOfWork:
  return UnitOfWork(session)
