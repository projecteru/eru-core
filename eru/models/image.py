# coding: utf-8

from datetime import datetime
from eru.models import db
from eru.models.base import Base


class Image(Base):
    __tablename__ = 'image'

    app_id = db.Column(db.Integer)
    version_id = db.Column(db.Integer)
    created = db.Column(db.DateTime, default=datetime.now)
    comment = db.Column(db.String(255), default='')
    image_url = db.Column(db.String(255))

    def __init__(self, app_id, version_id, image_url):
        self.app_id = app_id
        self.version_id = version_id
        self.image_url = image_url

    @classmethod
    def create(cls, app_id, version_id, image_url):
        image = cls(app_id, version_id, image_url)
        db.session.add(image)
        db.session.commit()
        return image

    @classmethod
    def get_by_app_and_version(cls, app_id, version_id):
        return cls.query.filter_by(app_id=app_id, version_id=version_id).first()

    @classmethod
    def list_by_app_id(cls, app_id, start=0, limit=20):
        q = cls.query.filter_by(app_id=app_id).order_by(cls.id.desc())
        return q[start:start+limit]

    @property
    def version(self):
        from .app import Version
        return Version.get(self.version_id)

    @property
    def app(self):
        from .app import App
        return App.get(self.app_id)
