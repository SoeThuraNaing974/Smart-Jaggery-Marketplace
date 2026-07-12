"""Admin batch image upload."""
import io


# 1x1 PNG
_PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")


def _fresh_id(client):
    return next(b["id"] for b in client.get("/api/batches").get_json() if b["batch_id"] == "B-FRESH")


def test_upload_batch_image(admin_client, customer_client):
    pk = _fresh_id(customer_client)
    data = {"file": (io.BytesIO(_PNG), "jaggery.png")}
    r = admin_client.post(f"/api/admin/batches/{pk}/image",
                          data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    path = r.get_json()["image_path"]
    assert path.endswith(".png")

    # batch listing now exposes the image_path
    b = next(x for x in customer_client.get("/api/batches").get_json() if x["id"] == pk)
    assert b["image_path"] == path


def test_reject_non_image(admin_client, customer_client):
    pk = _fresh_id(customer_client)
    data = {"file": (io.BytesIO(b"not an image"), "evil.txt")}
    r = admin_client.post(f"/api/admin/batches/{pk}/image",
                          data=data, content_type="multipart/form-data")
    assert r.status_code == 400


def test_remove_image(admin_client, customer_client):
    pk = _fresh_id(customer_client)
    admin_client.post(f"/api/admin/batches/{pk}/image",
                      data={"file": (io.BytesIO(_PNG), "j.png")}, content_type="multipart/form-data")
    assert admin_client.delete(f"/api/admin/batches/{pk}/image").status_code == 200
    b = next(x for x in customer_client.get("/api/batches").get_json() if x["id"] == pk)
    assert b["image_path"] is None


def test_customer_cannot_upload_image(customer_client):
    pk = _fresh_id(customer_client)
    r = customer_client.post(f"/api/admin/batches/{pk}/image",
                             data={"file": (io.BytesIO(_PNG), "j.png")}, content_type="multipart/form-data")
    assert r.status_code == 403
