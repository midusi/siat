class Base:
    def commit_and_refresh(self, obj):
        self.uow.commit()
        self.uow.refresh(obj)
        return obj
