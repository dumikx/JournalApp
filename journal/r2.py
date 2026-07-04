"""Client Cloudflare R2 (API compatibil S3) + helpere de presigning."""
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app, g


def _client():
    if "r2_client" not in g:
        cfg = current_app.config
        g.r2_client = boto3.client(
            "s3",
            endpoint_url=cfg["R2_ENDPOINT"],
            aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )
    return g.r2_client


def presign_put(key: str, content_type: str) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": current_app.config["R2_BUCKET"],
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=current_app.config["PRESIGN_EXPIRES"],
    )


def presign_get(key: str, download_filename: str | None = None) -> str:
    params = {"Bucket": current_app.config["R2_BUCKET"], "Key": key}
    if download_filename:
        params["ResponseContentDisposition"] = (
            f'attachment; filename="{download_filename}"'
        )
    return _client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=current_app.config["PRESIGN_EXPIRES"]
    )


def object_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=current_app.config["R2_BUCKET"], Key=key)
        return True
    except ClientError:
        return False


def delete_keys(keys: list[str]) -> None:
    if not keys:
        return
    client = _client()
    bucket = current_app.config["R2_BUCKET"]
    # delete_objects acceptă max 1000 de chei per apel; aici avem mult mai puține,
    # dar păstrăm împărțirea ca să nu depindem de limită.
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
        )
