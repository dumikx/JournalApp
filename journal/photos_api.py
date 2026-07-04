import re
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required
from sqlalchemy import func

from . import r2
from .extensions import db
from .models import Entry, Photo

bp = Blueprint("photos_api", __name__, url_prefix="/api")

_EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/gif": "gif",
    "image/avif": "avif",
}


def _key_pattern(entry_id: int) -> re.Pattern:
    return re.compile(
        rf"^journal/{entry_id}/[0-9a-f]{{32}}_(orig|display)\.[a-z0-9]{{2,5}}$"
    )


@bp.route("/entries/<int:entry_id>/photos/presign", methods=["POST"])
@login_required
def presign(entry_id):
    entry = db.session.get(Entry, entry_id)
    if entry is None:
        return jsonify({"error": "Intrarea nu există."}), 404

    data = request.get_json(silent=True) or {}
    requested = data.get("photos")
    if not isinstance(requested, list) or not requested:
        return jsonify({"error": "Cerere invalidă."}), 400

    max_photos = current_app.config["MAX_PHOTOS_PER_ENTRY"]
    if len(entry.photos) + len(requested) > max_photos:
        return (
            jsonify({"error": f"Maxim {max_photos} poze per intrare."}),
            400,
        )

    max_size = current_app.config["MAX_PHOTO_SIZE"]
    result = []
    for item in requested:
        content_type = str(item.get("content_type", ""))
        size = item.get("size", 0)
        if not content_type.startswith("image/"):
            return jsonify({"error": "Doar fișiere imagine sunt acceptate."}), 400
        if not isinstance(size, int) or size <= 0 or size > max_size:
            return (
                jsonify({"error": "Fișierul depășește limita de 25MB."}),
                400,
            )
        uid = uuid.uuid4().hex
        ext = _EXT_BY_TYPE.get(content_type, "bin")
        key_orig = f"journal/{entry_id}/{uid}_orig.{ext}"
        key_display = f"journal/{entry_id}/{uid}_display.jpg"
        result.append(
            {
                "uid": uid,
                "original": {
                    "key": key_orig,
                    "url": r2.presign_put(key_orig, content_type),
                    "content_type": content_type,
                },
                "display": {
                    "key": key_display,
                    "url": r2.presign_put(key_display, "image/jpeg"),
                    "content_type": "image/jpeg",
                },
            }
        )
    return jsonify({"photos": result})


@bp.route("/entries/<int:entry_id>/photos/confirm", methods=["POST"])
@login_required
def confirm(entry_id):
    entry = db.session.get(Entry, entry_id)
    if entry is None:
        return jsonify({"error": "Intrarea nu există."}), 404

    data = request.get_json(silent=True) or {}
    items = data.get("photos")
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Cerere invalidă."}), 400

    max_photos = current_app.config["MAX_PHOTOS_PER_ENTRY"]
    if len(entry.photos) + len(items) > max_photos:
        return jsonify({"error": f"Maxim {max_photos} poze per intrare."}), 400

    pattern = _key_pattern(entry_id)
    next_pos = (
        db.session.query(func.coalesce(func.max(Photo.position), -1))
        .filter(Photo.entry_id == entry_id)
        .scalar()
        + 1
    )

    created = []
    for item in items:
        key_orig = str(item.get("key_original", ""))
        key_display = str(item.get("key_display", ""))
        if not pattern.match(key_orig) or not pattern.match(key_display):
            return jsonify({"error": "Chei invalide."}), 400
        if not r2.object_exists(key_orig) or not r2.object_exists(key_display):
            return (
                jsonify({"error": "Upload-ul nu a fost găsit în R2 — reîncearcă."}),
                409,
            )
        photo = Photo(
            entry_id=entry_id,
            r2_key_original=key_orig,
            r2_key_display=key_display,
            position=next_pos,
        )
        next_pos += 1
        db.session.add(photo)
        db.session.flush()
        created.append(
            {
                "id": photo.id,
                "position": photo.position,
                "display_url": r2.presign_get(key_display),
            }
        )
    db.session.commit()
    return jsonify({"photos": created})


@bp.route("/photos/<int:photo_id>", methods=["DELETE"])
@login_required
def delete_photo(photo_id):
    photo = db.session.get(Photo, photo_id)
    if photo is None:
        return jsonify({"error": "Poza nu există."}), 404
    r2.delete_keys([photo.r2_key_original, photo.r2_key_display])
    db.session.delete(photo)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/entries/<int:entry_id>/photos/reorder", methods=["POST"])
@login_required
def reorder(entry_id):
    entry = db.session.get(Entry, entry_id)
    if entry is None:
        return jsonify({"error": "Intrarea nu există."}), 404

    data = request.get_json(silent=True) or {}
    order = data.get("order")
    photo_ids = {p.id for p in entry.photos}
    if (
        not isinstance(order, list)
        or {int(i) for i in order if isinstance(i, int)} != photo_ids
        or len(order) != len(photo_ids)
    ):
        return jsonify({"error": "Ordine invalidă."}), 400

    by_id = {p.id: p for p in entry.photos}
    for pos, pid in enumerate(order):
        by_id[pid].position = pos
    db.session.commit()
    return jsonify({"ok": True})
