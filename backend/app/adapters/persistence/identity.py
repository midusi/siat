from __future__ import annotations


class IdentityMap:
    def __init__(self):
        self._pairs: list[tuple[object, object]] = []

    def remember(self, domain, orm) -> None:
        for i, (d, _o) in enumerate(self._pairs):
            if d is domain:
                self._pairs[i] = (domain, orm)
                return
        self._pairs.append((domain, orm))

    def orm_for(self, domain):
        for d, orm in self._pairs:
            if d is domain:
                return orm
        return None

    def pairs(self):
        return list(self._pairs)

    def drop(self, domain) -> None:
        self._pairs = [(d, o) for d, o in self._pairs if d is not domain]

    def sync_pks(self) -> None:
        for domain, orm in self._pairs:
            if hasattr(domain, "id") and getattr(orm, "id", None) is not None:
                domain.id = orm.id
