from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TSVECTOR

from .extensions import db

# f_unaccent este un wrapper IMMUTABLE peste unaccent(), creat în migrația
# inițială — necesar pentru că o coloană generată cere funcții IMMUTABLE.
SEARCH_VECTOR_SQL = (
    "to_tsvector('simple', f_unaccent(coalesce(title, '') || ' ' || body))"
)


class Entry(db.Model):
    __tablename__ = "entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    search_vector = db.deferred(
        db.Column(TSVECTOR, db.Computed(SEARCH_VECTOR_SQL, persisted=True))
    )

    photos = db.relationship(
        "Photo",
        backref="entry",
        order_by="Photo.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Entry {self.entry_date}>"


class Photo(db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    r2_key_original = db.Column(db.String(500), nullable=False)
    r2_key_display = db.Column(db.String(500), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Photo {self.id} entry={self.entry_id}>"
