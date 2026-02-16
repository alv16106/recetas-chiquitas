"""Image upload: local filesystem or S3."""

from flask import current_app


S3_PREFIX = "s3/"


def use_s3():
    return bool(current_app.config.get("S3_BUCKET"))


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        region_name=current_app.config.get("S3_REGION", "eu-west-2"),
    )


def upload_image(recipe_id: int, file_content: bytes, unique_filename: str) -> str:
    """
    Upload image to S3; return storage key to save in RecipeImage.filename.
    unique_filename: e.g. uuid.ext
    Returns "s3/recipes/{recipe_id}/{unique_filename}"
    """
    if not use_s3():
        return None

    ext = unique_filename.rsplit(".", 1)[-1].lower() if "." in unique_filename else "jpg"
    key = f"{current_app.config['S3_PREFIX']}/{recipe_id}/{unique_filename}"
    client = _s3_client()
    bucket = current_app.config["S3_BUCKET"]
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_content,
        ContentType=f"image/{ext}" if ext != "jpg" else "image/jpeg",
    )
    return S3_PREFIX + key


def get_image_url(recipe_id: int, stored: str) -> str | None:
    """
    Return public URL or presigned URL for an S3-stored image.
    stored: "s3/recipes/123/abc.jpg"
    """
    if not use_s3() or not stored.startswith(S3_PREFIX):
        return None

    key = stored[len(S3_PREFIX) :]
    client = _s3_client()
    bucket = current_app.config["S3_BUCKET"]
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )
    return url


def delete_image(stored: str) -> None:
    """Delete image from S3. stored: 's3/recipes/123/abc.jpg'"""
    if not use_s3() or not stored.startswith(S3_PREFIX):
        return

    key = stored[len(S3_PREFIX) :]
    client = _s3_client()
    bucket = current_app.config["S3_BUCKET"]
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except Exception:
        pass


def delete_recipe_images(recipe_id: int, images) -> None:
    """Delete all S3 images for a recipe."""
    for img in images:
        if img.filename and img.filename.startswith(S3_PREFIX):
            delete_image(img.filename)
