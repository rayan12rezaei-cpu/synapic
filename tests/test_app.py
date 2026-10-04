from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_export_txt():
    response = client.post('/api/export', json={'text': 'hello', 'format': 'txt'})
    assert response.status_code == 200
    assert response.content == b'hello\n'
    assert 'attachment' in response.headers['content-disposition']
