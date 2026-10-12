# Hướng dẫn chạy Plane local từ đầu đến cuối

Tài liệu này dành cho repo hiện tại tại:

```text
/home/nguyenhongtantai/Programming/Project/ITACManagement
```

Cách chạy chuẩn là:

1. Chuẩn bị Docker và Node.js.
2. Tạo các file `.env` bằng `setup.sh`.
3. Kiểm tra các địa chỉ service bên trong Docker.
4. Chạy PostgreSQL, Valkey Redis, RabbitMQ, MinIO và các service API.
5. Chạy các frontend bằng `pnpm dev`.
6. Tạo tài khoản admin tại trang admin rồi đăng nhập ở web.

## 1. Các service và cổng

| Thành phần    |   Cổng | Cách chạy                    |
| ------------- | -----: | ---------------------------- |
| Web           | `3000` | `apps/web`, chạy bằng pnpm   |
| Admin         | `3001` | `apps/admin`, chạy bằng pnpm |
| Space         | `3002` | `apps/space`, chạy bằng pnpm |
| Live/realtime | `3100` | `apps/live`, chạy bằng pnpm  |
| Django API    | `8000` | container `api`              |
| PostgreSQL    | `5432` | container `plane-db`         |
| Valkey Redis  | `6379` | container `plane-redis`      |
| MinIO/S3      | `9000` | container `plane-minio`      |
| MinIO console | `9090` | container `plane-minio`      |

RabbitMQ chỉ dùng trong network Docker, không publish cổng ra host trong
`docker-compose-local.yml`.

## 2. Yêu cầu máy

Cần có:

- Docker Engine đang chạy và Docker Compose v2.
- Node.js `22.22.0` trở lên. Phiên bản repo được ghi trong `.node-version`.
- pnpm `11.10.0`. `setup.sh` sẽ kích hoạt bằng Corepack.
- Git.
- Tối thiểu nên có 12 GB RAM để build và chạy toàn bộ stack.
- Python `3.12` và `uv` chỉ cần nếu muốn chạy Django trực tiếp ngoài Docker.

Kiểm tra:

```bash
git --version
node --version
pnpm --version
docker --version
docker compose version
docker info >/dev/null && echo "Docker daemon: OK"
free -h
df -h .
```

Nếu máy chưa có Node đúng phiên bản, có thể dùng `mise`, `nvm` hoặc trình
quản lý Node khác. Sau khi đổi phiên bản, kiểm tra lại `node --version` trước
khi chạy setup.

### Sửa lỗi Docker permission

Nếu gặp lỗi:

```text
permission denied while trying to connect to the Docker daemon socket
```

thực hiện một lần bằng tài khoản có quyền quản trị:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

Nếu `sudo` yêu cầu mật khẩu mà tài khoản hiện tại không có quyền, cần nhờ
quản trị viên thêm user vào group `docker`. Không nên chạy toàn bộ project bằng
`sudo`, vì các file tạo ra sẽ thuộc về root và gây lỗi permission cho pnpm.

## 3. Tạo environment và cài dependency

Mở terminal, chạy đúng từ thư mục gốc:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
chmod +x setup.sh
./setup.sh
```

Kiểm tra setup đã tạo đủ file và dependency:

```bash
test -f .env && echo "root .env: OK"
test -f apps/api/.env && echo "api .env: OK"
test -f apps/web/.env && echo "web .env: OK"
test -f apps/admin/.env && echo "admin .env: OK"
test -f apps/space/.env && echo "space .env: OK"
test -f apps/live/.env && echo "live .env: OK"
test -d node_modules && echo "node_modules: OK"
pnpm --version
```

Script này sẽ:

- copy `.env.example` thành `.env` ở root và trong `apps/web`, `apps/admin`,
  `apps/space`, `apps/live`, `apps/api`;
- thêm Django `SECRET_KEY` vào `apps/api/.env`;
- bật pnpm bằng Corepack;
- chạy `pnpm install`.

`setup.sh` copy đè các file `.env`. Nếu đã tự chỉnh biến môi trường, hãy sao
lưu chúng trước khi chạy lại script. Không chạy lại script mỗi lần khởi động,
vì mỗi lần chạy sẽ thêm một `SECRET_KEY` mới.

## 4. Kiểm tra env cho Docker

API chạy trong container nên phải dùng tên service Docker, không dùng
`localhost` cho database, Redis hoặc MinIO. Sau khi chạy setup, mở
`apps/api/.env` và bảo đảm các dòng sau có giá trị tương ứng:

```dotenv
POSTGRES_HOST="plane-db"
REDIS_HOST="plane-redis"
REDIS_URL="redis://plane-redis:6379/"
AWS_S3_ENDPOINT_URL="http://plane-minio:9000"
USE_MINIO=1
```

Có thể cập nhật tự động bằng các lệnh sau:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
sed -i -E 's|^POSTGRES_HOST=.*|POSTGRES_HOST="plane-db"|' apps/api/.env
sed -i -E 's|^REDIS_HOST=.*|REDIS_HOST="plane-redis"|' apps/api/.env
sed -i -E 's|^REDIS_URL=.*|REDIS_URL="redis://plane-redis:6379/"|' apps/api/.env
sed -i -E 's|^AWS_S3_ENDPOINT_URL=.*|AWS_S3_ENDPOINT_URL="http://plane-minio:9000"|' apps/api/.env
sed -i -E 's|^USE_MINIO=.*|USE_MINIO=1|' apps/api/.env
```

Xác nhận các giá trị quan trọng mà không in secret:

```bash
grep -E '^(POSTGRES_HOST|REDIS_HOST|REDIS_URL|AWS_S3_ENDPOINT_URL|USE_MINIO)=' apps/api/.env
grep -E '^(VITE_API_BASE_URL|VITE_ADMIN_BASE_PATH|VITE_SPACE_BASE_PATH)=' apps/web/.env apps/admin/.env apps/space/.env
```

Kiểm tra Compose trước khi khởi động. Lệnh này chỉ parse cấu hình, không start
container:

```bash
docker compose -f docker-compose-local.yml config --quiet
echo "Docker Compose config: OK"
```

Không đưa secret thật vào Git. Các giá trị mặc định trong file example chỉ
dành cho môi trường local.

## 5. Khởi động backend bằng Docker

Từ thư mục gốc:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml up -d --build
```

Nếu muốn xem log ngay trong lúc khởi động lần đầu, dùng lệnh foreground trong
Terminal 1 thay cho lệnh `-d`:

```bash
docker compose -f docker-compose-local.yml up --build
```

Khi log đã ổn định, nhấn `Ctrl+C`, sau đó chạy lại ở chế độ nền:

```bash
docker compose -f docker-compose-local.yml up -d
```

Lần đầu có thể mất nhiều thời gian vì Docker phải build image API và cài
dependency Python. Kiểm tra trạng thái tất cả container:

```bash
docker compose -f docker-compose-local.yml ps -a
```

Trạng thái bình thường:

- `plane-db`, `plane-redis`, `plane-mq`, `plane-minio`, `api`, `worker` và
  `beat-worker` đang chạy.
- `migrator` có thể ở trạng thái `Exited (0)` vì đây là job chạy migration một
  lần, không phải service chạy liên tục.

Xem log theo service:

```bash
docker compose -f docker-compose-local.yml logs --tail=200 migrator
docker compose -f docker-compose-local.yml logs --tail=200 api
docker compose -f docker-compose-local.yml logs -f worker
```

Kiểm tra các container dependency từ bên trong API container:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py check --settings=plane.settings.local
docker compose -f docker-compose-local.yml exec api python manage.py showmigrations --plan | tail -n 20
```

Kết quả của lệnh `check` phải là `System check identified no issues`.

Kiểm tra API đã lắng nghe:

```bash
curl -i http://127.0.0.1:8000/api/instances/
```

API có thể trả `401` hoặc `403` tùy endpoint và trạng thái instance; điều đó
vẫn chứng minh API đã reachable. Nếu curl báo `connection refused`, xem log
`api` trước khi chạy frontend.

## 6. Khởi động frontend

Mở terminal thứ hai:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
pnpm dev
```

Giữ terminal này đang chạy. Mở Terminal 3 để kiểm tra HTTP:

```bash
curl -fsS -o /dev/null -w 'web: %{http_code}\n' http://127.0.0.1:3000/
curl -fsS -o /dev/null -w 'admin: %{http_code}\n' http://127.0.0.1:3001/god-mode/
curl -fsS -o /dev/null -w 'space: %{http_code}\n' http://127.0.0.1:3002/spaces/
curl -fsS -o /dev/null -w 'live: %{http_code}\n' http://127.0.0.1:3100/
```

Nếu một app chưa chạy, chỉ khởi động riêng app đó trong một terminal khác:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
pnpm --filter web dev
```

Lệnh root chạy các app có script `dev` qua Turbo. Mở các địa chỉ:

- Web: <http://localhost:3000>
- Admin: <http://localhost:3001/god-mode/>
- Space: <http://localhost:3002/spaces/>
- Live: <http://localhost:3100>

Nếu chỉ cần một app:

```bash
pnpm --filter web dev
pnpm --filter admin dev
pnpm --filter space dev
pnpm --filter live dev
```

Trong terminal chạy `pnpm dev`, giữ nguyên tiến trình để hot reload hoạt động.

## 7. Tạo tài khoản và kiểm tra lần đầu

1. Mở <http://localhost:3001/god-mode/>.
2. Đăng ký tài khoản instance admin.
3. Mở <http://localhost:3000>.
4. Đăng nhập bằng tài khoản vừa tạo.
5. Nếu cần public workspace, kiểm tra thêm <http://localhost:3002/spaces/>.

Các file frontend đã được setup để gọi API tại `http://localhost:8000` và dùng
đúng các base path `/god-mode`, `/spaces`, `/live`.

## 8. Dừng và khởi động lại

Dừng frontend bằng `Ctrl+C` trong terminal `pnpm dev`. Dừng backend:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml down
```

Lần sau, nếu không đổi dependency hoặc Dockerfile, chỉ cần:

```bash
docker compose -f docker-compose-local.yml up -d
pnpm dev
```

Không dùng `down -v` trừ khi muốn xóa toàn bộ dữ liệu local trong PostgreSQL,
Redis, RabbitMQ và MinIO:

```bash
docker compose -f docker-compose-local.yml down -v
```

Trước khi chạy lại sau khi dừng, kiểm tra không còn container cũ bị lỗi:

```bash
docker compose -f docker-compose-local.yml ps -a
docker compose -f docker-compose-local.yml up -d
```

## 9. Chạy Django trực tiếp trên host để debug

Chỉ dùng cách này khi cần debug Python. Không chạy đồng thời API container và
Django host trên cùng cổng `8000`.

### 9.1. Chuẩn bị Python

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement/apps/api
uv python install 3.12
uv python pin 3.12
uv sync
uv run python --version
```

Kiểm tra Python và Django đang lấy từ môi trường uv:

```bash
uv run python -c 'import sys, django; print(sys.executable); print(django.get_version())'
```

Kết quả phải là Python `3.12.x`.

### 9.2. Chạy các dependency bằng Docker

Nếu stack đầy đủ đang chạy, dừng các service ứng dụng trước:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml stop api worker beat-worker migrator
docker compose -f docker-compose-local.yml up -d plane-db plane-redis plane-mq plane-minio
```

Xác nhận bốn dependency đã chạy:

```bash
docker compose -f docker-compose-local.yml ps plane-db plane-redis plane-mq plane-minio
```

### 9.3. Nạp env host và chạy migration/API

Mở terminal mới:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement/apps/api
set -a
source .env
set +a
export DJANGO_SETTINGS_MODULE=plane.settings.local
export POSTGRES_HOST=127.0.0.1
export DATABASE_URL=postgresql://plane:plane@127.0.0.1:5432/plane
export REDIS_HOST=127.0.0.1
export REDIS_URL=redis://127.0.0.1:6379/
export RABBITMQ_HOST=127.0.0.1
export AWS_S3_ENDPOINT_URL=http://127.0.0.1:9000
export USE_MINIO=1
python -c 'import os; print("POSTGRES_HOST=", os.environ["POSTGRES_HOST"]); print("REDIS_URL=", os.environ["REDIS_URL"]); print("AWS_S3_ENDPOINT_URL=", os.environ["AWS_S3_ENDPOINT_URL"])'
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

Trong chế độ này, các service host phải dùng `127.0.0.1`; không đổi file
`apps/api/.env` sang host nếu vẫn muốn dùng Docker API sau đó. Nếu chạy
`makemigrations`, dùng cùng các biến môi trường ở trên:

```bash
uv run python manage.py makemigrations
```

## 10. Xử lý lỗi thường gặp

### Docker không chạy hoặc permission denied

Kiểm tra:

```bash
docker info
docker ps
```

Nếu muốn xem service nào đang chạy và log lỗi ngắn:

```bash
docker compose -f docker-compose-local.yml ps -a
docker compose -f docker-compose-local.yml logs --tail=100 api plane-db plane-redis plane-minio
```

Nếu thiếu quyền, làm theo mục 2. Nếu Docker daemon chưa chạy, khởi động Docker
theo cách phù hợp với distro Linux của máy.

### `apps/api/.env: no such file or directory`

Chạy lại `./setup.sh` từ thư mục gốc. Nếu file đã có nhưng bị sai, đối chiếu
với `apps/api/.env.example` và mục 4.

### `REDIS_URL` là `None` hoặc lỗi `startswith`

Không chạy Django trước khi nạp env. Khi chạy host, phải có cả:

```bash
export DJANGO_SETTINGS_MODULE=plane.settings.local
export REDIS_URL=redis://127.0.0.1:6379/
```

Khi chạy container, kiểm tra lại `REDIS_URL=redis://plane-redis:6379/` trong
`apps/api/.env`.

### API container không kết nối được PostgreSQL/Redis/MinIO

Trong container phải dùng `plane-db`, `plane-redis`, `plane-minio`, không dùng
`localhost`. Xem lại mục 4, sau đó rebuild:

```bash
docker compose -f docker-compose-local.yml up -d --build
```

### Port đã được sử dụng

Kiểm tra tiến trình đang chiếm cổng:

```bash
ss -ltnp | grep -E ':3000|:3001|:3002|:3100|:8000|:5432|:6379|:9000'
```

Dừng stack cũ hoặc tiến trình cũ trước khi khởi động lại. Không đổi port frontend
một cách tùy ý nếu chưa cập nhật các biến `VITE_*` và base URL tương ứng.

### Frontend mở được nhưng không gọi được API

Kiểm tra API bằng curl ở mục 5, sau đó kiểm tra các file:

- `apps/web/.env`
- `apps/admin/.env`
- `apps/space/.env`
- `apps/live/.env`

Các biến `VITE_API_BASE_URL` phải là `http://localhost:8000`.

Kiểm tra nhanh:

```bash
grep -R --line-number '^VITE_API_BASE_URL=' apps/web/.env apps/admin/.env apps/space/.env apps/live/.env
curl -i http://127.0.0.1:8000/api/instances/
```

### Dữ liệu local bị lỗi hoặc muốn chạy sạch

Lệnh sau xóa dữ liệu persistent, chỉ dùng khi chấp nhận mất dữ liệu local:

```bash
docker compose -f docker-compose-local.yml down -v
docker compose -f docker-compose-local.yml up -d --build
```

## 11. Kiểm tra code trước khi gửi thay đổi

Từ thư mục gốc:

```bash
pnpm check:format
pnpm check:lint
pnpm check:types
```

Có thể chạy toàn bộ bằng:

```bash
pnpm check
```

Backend test dùng Docker test stack riêng, không dùng database local đang chạy:

```bash
docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests
```

## 12. Tóm tắt lệnh chạy hằng ngày

Sau khi setup thành công và đã chỉnh `apps/api/.env` cho network Docker:

Terminal 1:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml up -d
docker compose -f docker-compose-local.yml ps -a
curl -i http://127.0.0.1:8000/api/instances/
```

Terminal 2:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
pnpm dev
```

Terminal 3, tùy chọn:

```bash
curl -fsS -o /dev/null -w 'web: %{http_code}\n' http://127.0.0.1:3000/
curl -fsS -o /dev/null -w 'admin: %{http_code}\n' http://127.0.0.1:3001/god-mode/
```

Truy cập <http://localhost:3001/god-mode/> trước, sau đó dùng
<http://localhost:3000>.

## Tài liệu liên quan

- [README.md](README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [AGENTS.md](AGENTS.md)
- [apps/api/tests/RUNNING_TESTS.md](apps/api/tests/RUNNING_TESTS.md)

## 13. Yêu cầu quản lý tài khoản và database

Phần này mô tả đúng trạng thái hiện tại của repo và cách triển khai yêu cầu:

1. Không cho người dùng tự đăng ký tài khoản.
2. Chỉ có một tài khoản super admin quản lý thành viên.
3. Super admin xem được số lượng tài khoản.
4. Super admin xem dữ liệu database theo cơ chế an toàn.

### 13.1. Tắt đăng ký công khai

Repo đã có sẵn cấu hình `ENABLE_SIGNUP`. Khi giá trị là `0`, người dùng không
được tự đăng ký nếu không có lời mời. Không xóa toàn bộ endpoint signup ngay,
vì luồng đăng ký qua lời mời vẫn có thể cần cho thành viên được mời vào
workspace.

#### Cách 1: tắt bằng giao diện God Mode

1. Khởi động backend và admin theo mục 5 và mục 6.
2. Mở <http://localhost:3001/god-mode/>.
3. Đăng nhập bằng instance admin đầu tiên.
4. Vào **Authentication**.
5. Tắt **Allow anyone to sign up even without an invite**.
6. Kiểm tra công tắc đã ở trạng thái tắt rồi đăng xuất/đăng nhập lại.

#### Cách 2: tắt bằng database configuration

Khi cần đặt chắc chắn bằng lệnh, chạy:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.license.models import InstanceConfiguration; c, _ = InstanceConfiguration.objects.get_or_create(key="ENABLE_SIGNUP", defaults={"value": "0", "category": "authentication", "is_encrypted": False}); c.value = "0"; c.save(update_fields=["value"]); print("ENABLE_SIGNUP=0")'
```

Sau đó xóa cache instance và khởi động lại API:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py clear_cache
docker compose -f docker-compose-local.yml restart api worker beat-worker
```

Kiểm tra cấu hình API đang trả về `enable_signup=false`:

```bash
curl -s http://127.0.0.1:8000/api/instances/ | python -m json.tool | grep -A1 'enable_signup'
```

Nếu chạy hoàn toàn bằng Docker và muốn đặt mặc định ngay từ env, thêm dòng sau
vào `apps/api/.env` rồi build lại:

```dotenv
ENABLE_SIGNUP=0
```

```bash
docker compose -f docker-compose-local.yml up -d --build api worker beat-worker
```

Lưu ý: cấu hình trong `InstanceConfiguration` có thể được ưu tiên hơn giá trị
env sau khi đã được lưu từ God Mode. Vì vậy nên kiểm tra bằng API thay vì chỉ
đọc file `.env`.

### 13.2. Tạo tài khoản super admin đầu tiên

Repo hiện tạo instance admin đầu tiên qua trang setup của God Mode:

```text
http://localhost:3001/god-mode/
```

Làm theo thứ tự:

1. Trước khi có admin, mở trang God Mode.
2. Nhập email, họ tên và mật khẩu mạnh.
3. Hoàn tất setup instance.
4. Đăng nhập lại bằng tài khoản vừa tạo.
5. Tắt `ENABLE_SIGNUP` theo mục 13.1.

Tài khoản này là **instance admin** của Plane, không đồng nghĩa hoàn toàn với
`is_superuser=True` của Django. Quyền God Mode hiện được kiểm tra qua bảng
`InstanceAdmin` và role từ `15` trở lên.

Kiểm tra admin hiện tại bằng Docker:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.license.models import InstanceAdmin; print(list(InstanceAdmin.objects.values("user__email", "role", "user__is_active")))'
```

### 13.3. Giới hạn chỉ một super admin

Code hiện tại cho phép có nhiều `InstanceAdmin`, nên việc chỉ giữ một super
admin cần được quy định bằng quy trình và kiểm tra dữ liệu:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.license.models import InstanceAdmin; print(InstanceAdmin.objects.count()); print(list(InstanceAdmin.objects.values("id", "user__email", "role")))'
```

Không nên biến tất cả thành viên thành `is_superuser=True`. Kiến trúc nên dùng:

- một bản ghi `InstanceAdmin` role cao nhất cho tài khoản quản trị chính;
- các thành viên thông thường chỉ là `User` và được thêm vào workspace/project;
- nếu cần admin dự phòng, tạo một instance admin thứ hai có role thấp hơn và
  ghi nhận rõ người được cấp quyền.

Nếu bắt buộc hệ thống phải **chặn tuyệt đối** admin thứ hai, cần thêm thay đổi
backend ở `InstanceAdminEndpoint.post`: từ chối tạo bản ghi mới khi đã có admin
chính, đồng thời thêm test cho trường hợp request thứ hai. Không nên chỉ ẩn nút
trên frontend vì người dùng vẫn có thể gọi API trực tiếp.

### 13.4. Super admin tạo tài khoản thành viên

Hiện tại God Mode chưa có màn hình hoàn chỉnh để super admin tạo `User` mới.
Endpoint `POST /api/instances/admins/` hiện chỉ nhận email của một user đã tồn
tại để cấp quyền instance admin; endpoint này không phải API tạo thành viên.

Để đáp ứng đúng yêu cầu, cần phát triển một module quản lý thành viên gồm:

1. API chỉ cho instance admin chính gọi:
   - `GET /api/instance-members/`: danh sách tài khoản và trạng thái;
   - `POST /api/instance-members/`: tạo user với email, họ tên, mã số, chức vụ;
   - `PATCH /api/instance-members/<id>/`: khóa/mở khóa hoặc cập nhật thông tin;
   - `DELETE /api/instance-members/<id>/`: vô hiệu hóa, không xóa cứng mặc định;
   - `GET /api/instance-members/count/`: trả tổng số tài khoản.
2. Backend dùng `InstanceAdminPermission` và thêm kiểm tra user hiện tại là
   tài khoản super admin duy nhất, không tin vào cờ từ frontend.
3. Mật khẩu phải được tạo bằng `set_password()` hoặc `make_password()`, không
   lưu plain text.
4. Nên gửi email đặt mật khẩu lần đầu; nếu chưa có SMTP thì tạo mật khẩu tạm,
   buộc đổi mật khẩu ở lần đăng nhập đầu tiên và không ghi mật khẩu vào log.
5. Khi khóa tài khoản, đặt `is_active=False` và thu hồi session/token; không
   xóa user ngay vì user còn liên kết với issue, workspace và audit history.
6. Thêm test cho quyền truy cập, email trùng, tạo user, khóa user và đếm user.

Ví dụ lệnh tạo tài khoản thủ công hiện có thể dùng trong lúc chưa có UI. Lệnh
này chạy bên trong API container và không gửi email:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from django.contrib.auth import get_user_model; User = get_user_model(); email="member@example.com"; u, created = User.objects.get_or_create(email=email, defaults={"username": "member_example", "first_name": "Member", "is_active": True}); u.set_password("CHANGE_THIS_NOW"); u.is_password_reset_required=True; u.save(); print("created=" + str(created) + ", id=" + str(u.id))'
```

Không dùng mật khẩu mẫu ở trên cho tài khoản thật. Sau khi tạo user, cần thêm
user vào workspace/project bằng flow **Invite members** hoặc module thành viên
mới. Tạo `User` riêng lẻ chưa tự cấp quyền truy cập workspace.

### 13.5. Xem số lượng tài khoản

Trong lúc chưa có dashboard riêng, super admin có thể kiểm tra bằng lệnh
read-only:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.db.models import User; print({"total": User.objects.count(), "active": User.objects.filter(is_active=True).count(), "inactive": User.objects.filter(is_active=False).count()})'
```

Khi làm giao diện, chỉ trả về số liệu tổng hợp như `total`, `active`, `inactive`
và phân trang danh sách. Không trả toàn bộ password hash, token, session hoặc
secret fields về frontend.

### 13.6. Xem database an toàn

Không nên cho frontend có quyền chạy SQL tùy ý. Cách an toàn hơn là:

- super admin xem danh sách và số liệu qua API được allowlist;
- truy vấn dữ liệu nhạy cảm chỉ chạy từ terminal hoặc công cụ quản trị nội bộ;
- tài khoản database dùng để xem dữ liệu nên là read-only;
- ghi audit log cho hành động xem, export và thay đổi dữ liệu;
- không cho endpoint nhận trực tiếp SQL từ request.

#### Xem database PostgreSQL bằng psql

Mở psql trong container database:

```bash
cd /home/nguyenhongtantai/Programming/Project/ITACManagement
docker compose -f docker-compose-local.yml exec plane-db psql -U plane -d plane
```

Trong psql, dùng các lệnh chỉ đọc:

```sql
\dt
\d users
SELECT COUNT(*) AS total_users FROM users;
SELECT id, email, username, is_active, is_superuser, created_at FROM users ORDER BY created_at DESC LIMIT 50;
\q
```

Hoặc chạy một câu lệnh từ shell mà không vào interactive mode:

```bash
docker compose -f docker-compose-local.yml exec -T plane-db \
  psql -U plane -d plane -c 'SELECT COUNT(*) AS total_users FROM users;'
```

#### Sao lưu trước khi thao tác database

```bash
mkdir -p backups
docker compose -f docker-compose-local.yml exec -T plane-db \
  pg_dump -U plane -d plane > backups/plane-$(date +%Y%m%d-%H%M%S).sql
```

Không chạy `DROP`, `TRUNCATE`, `DELETE` hoặc `UPDATE` trực tiếp trên production
chỉ vì muốn “xem database”. Luôn backup và dùng migration/management command
cho thay đổi dữ liệu.

### 13.7. Import user từ file CSV

Có thể tạo tài khoản hàng loạt bằng command `import_users`. Command đọc CSV UTF-8,
hỗ trợ `--dry-run`, tạo `User` và `Profile`, đồng thời tùy chọn thêm user vào
workspace đã tồn tại.

```bash
docker compose -f docker-compose-local.yml exec api python manage.py import_users users.csv
```

Chỉ thêm `--workspace-slug itac` khi workspace `itac` đã tồn tại:

```bash
docker compose -f docker-compose-local.yml exec api \
  python manage.py import_users users.csv --workspace-slug itac
```

Command này phải thực hiện trong một transaction cho từng dòng và cần:

1. Kiểm tra email hợp lệ, chuẩn hóa thành chữ thường và loại bỏ khoảng trắng.
2. Từ chối email trùng trong CSV hoặc báo rõ dòng bị trùng trong database.
3. Tạo `User` bằng `set_password()`, không bao giờ lưu mật khẩu dạng plain text.
4. Tạo `Profile` tương ứng cho user.
5. Nếu CSV có workspace thì tạo hoặc cập nhật `WorkspaceMember`; nếu chưa có
   workspace thì chỉ tạo tài khoản và `Profile`.
6. Không ghi mật khẩu vào log, output terminal hoặc file report.
7. Có chế độ `--dry-run` để kiểm tra CSV trước khi ghi database.
8. Có report gồm `created`, `updated`, `skipped`, `failed` và số dòng lỗi.

#### CSV tạo tài khoản khi chưa có workspace/project

Nếu hiện tại chưa có workspace hoặc project, không cần đưa
`workspace_slug`, `workspace_role`, `project_identifier` hoặc `project_role` vào
CSV. Dùng mẫu tối thiểu sau:

```csv
email,username,first_name,last_name,mssv,chuc_vu,ngay_sinh,initial_password
nguyen.van.a@example.com,nguyenvana,Nguyen,Van A,SV001,Sinh vien,2004-05-12,MatKhauTamThayDoi_2026!
tran.thi.b@example.com,tranthib,Tran,Thi B,SV002,Giang vien,1990-11-20,MatKhauTamThayDoi_2026!
```

Tài khoản tạo theo mẫu này có thể đăng nhập, nhưng chưa thuộc workspace nào.
Sau khi tạo workspace, cần thêm user vào workspace rồi mới thêm user vào từng
project.

#### CSV tối thiểu khi workspace đã tồn tại

CSV dùng dấu phẩy, encoding UTF-8, dòng đầu là header:

```csv
email,username,first_name,last_name,mssv,chuc_vu,ngay_sinh,workspace_slug,workspace_role,initial_password
nguyen.van.a@example.com,nguyenvana,Nguyen,Van A,SV001,Sinh vien,2004-05-12,itac,5,MatKhauTamThayDoi_2026!
tran.thi.b@example.com,tranthib,Tran,Thi B,SV002,Giang vien,1990-11-20,itac,15,MatKhauTamThayDoi_2026!
```

Ý nghĩa các cột:

| Cột                | Bắt buộc                                 | Nội dung                                                                                       |
| ------------------ | ---------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `email`            | Có                                       | Email duy nhất để đăng nhập.                                                                   |
| `username`         | Có                                       | Username duy nhất, chỉ dùng chữ, số, `_` hoặc `-`.                                             |
| `first_name`       | Có                                       | Tên hoặc tên gọi của thành viên.                                                               |
| `last_name`        | Không                                    | Họ và tên đệm.                                                                                 |
| `mssv`             | Không                                    | Mã số sinh viên hoặc mã nhân sự.                                                               |
| `chuc_vu`          | Không                                    | Chức vụ.                                                                                       |
| `ngay_sinh`        | Không                                    | Định dạng `YYYY-MM-DD`.                                                                        |
| `workspace_slug`   | Không, nếu chưa có workspace             | Slug workspace đã tồn tại, ví dụ `itac`.                                                       |
| `workspace_role`   | Không, nếu chưa có workspace             | `5` cho member thông thường; chỉ dùng `15` hoặc `20` khi thật sự cần quyền quản trị workspace. |
| `initial_password` | Có nếu muốn đăng nhập bằng mật khẩu ngay | Mật khẩu tạm đủ mạnh. Command chỉ lưu hash của mật khẩu này.                                   |

`display_name` có thể được tự tạo từ `first_name` và `last_name`; không cần thêm
cột riêng nếu không có yêu cầu khác. `id`, `password hash`, `date_joined`,
`is_active`, `is_email_verified` và các token hệ thống không được đưa vào CSV;
backend tự sinh các giá trị này.

#### Cách an toàn hơn: không đưa mật khẩu vào CSV

Nếu chưa có workspace, khuyến nghị file CSV chỉ có các cột sau:

```csv
email,username,first_name,last_name,mssv,chuc_vu,ngay_sinh
nguyen.van.a@example.com,nguyenvana,Nguyen,Van A,SV001,Sinh vien,2004-05-12
```

Khi đó importer sẽ tạo mật khẩu ngẫu nhiên đủ mạnh và xuất một file kết quả
được bảo vệ riêng, hoặc gửi email đặt mật khẩu nếu SMTP đã cấu hình. Không gửi
file chứa mật khẩu qua Git, Slack, email nhóm hoặc commit vào repository.

Nếu cần đặt mật khẩu thủ công sau khi import, dùng lệnh tương tác để mật khẩu
không xuất hiện trong shell history:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py reset_password user@example.com
```

#### Quy trình import được khuyến nghị

Đặt file CSV ở thư mục tạm, không đặt trong repository:

```bash
mkdir -p /tmp/plane-import
cp users.csv /tmp/plane-import/users.csv
chmod 600 /tmp/plane-import/users.csv
```

Chạy kiểm tra trước, chưa ghi database:

```bash
docker compose -f docker-compose-local.yml exec api \
  python manage.py import_users /code/tmp/plane-import/users.csv \
  --dry-run
```

Trước lệnh trên, copy file từ host vào thư mục `/code` đã được mount vào
container API:

```bash
mkdir -p apps/api/tmp/plane-import
cp /tmp/plane-import/users.csv apps/api/tmp/plane-import/users.csv
chmod 600 apps/api/tmp/plane-import/users.csv
```

Nếu report không có lỗi, backup database rồi mới import thật:

```bash
mkdir -p backups
docker compose -f docker-compose-local.yml exec -T plane-db \
  pg_dump -U plane -d plane > backups/plane-before-user-import-$(date +%Y%m%d-%H%M%S).sql

docker compose -f docker-compose-local.yml exec api \
  python manage.py import_users /code/tmp/plane-import/users.csv
```

Kiểm tra sau import:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.db.models import User, WorkspaceMember; print("users=", User.objects.count()); print("active=", User.objects.filter(is_active=True).count()); print("workspace_members=", WorkspaceMember.objects.count())'
```

Sau khi xác nhận thành công, xóa file CSV và report có chứa thông tin nhạy cảm:

```bash
rm -f /tmp/plane-import/users.csv /tmp/plane-import/import-report.csv
rm -f apps/api/tmp/plane-import/users.csv apps/api/tmp/plane-import/import-report.csv
```

### 13.8. Vai trò riêng theo từng project

Một user có thể tham gia nhiều project với các role khác nhau. Không nên đặt
`project_role` vào cùng một dòng user nếu một user có nhiều project, vì sẽ khó
biểu diễn quan hệ nhiều-nhiều. Thiết kế đúng là tách thành hai nhóm dữ liệu:

- `User`: thông tin tài khoản dùng để đăng nhập;
- `WorkspaceMember`: user thuộc workspace nào;
- `ProjectMember`: user thuộc project nào và role gì trong project đó.

Repo hiện đã có model `ProjectMember` với các role:

| Giá trị | Tên    | Quyền                                                                  |
| ------: | ------ | ---------------------------------------------------------------------- |
|    `20` | Admin  | Leader/project admin; có thể quản lý thành viên và role trong project. |
|    `15` | Member | Thành viên thực hiện công việc trong project.                          |
|     `5` | Guest  | Quyền xem hạn chế, tùy feature.                                        |

Ví dụ cùng một user có thể có dữ liệu như sau:

```text
nguyen.van.a@example.com -> Project ITAC-WEB: role 20 (leader)
nguyen.van.a@example.com -> Project ITAC-MOBILE: role 15 (member)
nguyen.van.a@example.com -> Project ITAC-REPORT: role 5 (guest)
```

#### Quyền của project leader

Project leader phải là `ProjectMember.role=20`, không phải chỉ là tên hiển thị
trong frontend. Leader có thể:

1. Xem danh sách thành viên của project.
2. Thêm thành viên workspace vào project.
3. Đổi role của thành viên trong project.
4. Hạ role hoặc vô hiệu hóa thành viên theo các giới hạn bảo mật.
5. Không tự hạ role hoặc tự xóa mình nếu project chỉ còn một admin.

Backend hiện đã kiểm tra các điều kiện chính:

- người gọi phải là thành viên active của đúng project;
- chỉ project admin hoặc workspace admin mới được thay đổi role;
- project leader không được tự đổi role của chính mình;
- không được đổi role của người có role bằng hoặc cao hơn mình;
- không được cấp project role cao hơn workspace role của người nhận;
- không được hạ workspace admin thành project member thông thường từ project.
- thao tác rời project đã kiểm tra trường hợp leader cuối cùng; cần bổ sung cùng
  kiểm tra này cho API hạ role hoặc vô hiệu hóa leader cuối cùng.

Frontend chỉ điều khiển hiển thị. Không được chỉ dựa vào việc ẩn nút đổi role;
mọi kiểm tra quyền phải tiếp tục nằm ở API backend.

#### Sau khi tạo workspace/project

Quy trình tiếp theo là:

1. Tạo workspace bằng tài khoản super admin.
2. Thêm các user đã import vào workspace.
3. Tạo các project trong workspace.
4. Dùng file `project-members.csv` để gán role riêng cho từng user trong từng
   project.

User có thể tồn tại trong database trước khi workspace/project được tạo. Không
được dùng `workspace_slug` hoặc `project_identifier` giả, vì importer phải
kiểm tra các đối tượng này đã tồn tại.

#### CSV cho membership của nhiều project

Giữ file user và file phân quyền project riêng nhau. File thứ hai có một dòng
cho mỗi quan hệ user-project:

```csv
email,workspace_slug,project_identifier,project_role
nguyen.van.a@example.com,itac,ITAC-WEB,20
nguyen.van.a@example.com,itac,ITAC-MOBILE,15
nguyen.van.a@example.com,itac,ITAC-REPORT,5
tran.thi.b@example.com,itac,ITAC-WEB,15
tran.thi.b@example.com,itac,ITAC-MOBILE,20
```

Ý nghĩa:

| Cột                  | Bắt buộc | Nội dung                                             |
| -------------------- | -------- | ---------------------------------------------------- |
| `email`              | Có       | Phải trùng user đã được import ở bước trước.         |
| `workspace_slug`     | Có       | Workspace chứa project.                              |
| `project_identifier` | Có       | Identifier của project đã tồn tại, ví dụ `ITAC-WEB`. |
| `project_role`       | Có       | Chỉ nhận `20`, `15` hoặc `5`.                        |

Importer project phải kiểm tra:

1. User đã tồn tại và là active `WorkspaceMember` của workspace.
2. Project tồn tại và thuộc đúng workspace.
3. Không tạo trùng `ProjectMember` active.
4. Một project phải luôn còn ít nhất một leader role `20`; backend cần chặn việc
   hạ role hoặc vô hiệu hóa leader cuối cùng.
5. User workspace role `5` không được nhận project role `15` hoặc `20`.
6. Import nhiều project phải chạy transaction theo từng dòng và có report lỗi.

Command đề xuất:

```bash
docker compose -f docker-compose-local.yml exec api \
  python manage.py import_project_members /code/tmp/plane-import/project-members.csv \
  --dry-run
```

Sau khi kiểm tra và backup database:

```bash
docker compose -f docker-compose-local.yml exec api \
  python manage.py import_project_members /code/tmp/plane-import/project-members.csv
```

`import_project_members` vẫn là command cần phát triển thêm; hiện tại repo đã có
`import_users`, model và API role nhưng chưa có CSV importer project hoàn chỉnh.

#### Cách thao tác trên giao diện hiện tại

Sau khi user đã thuộc workspace và project:

1. Mở Web tại <http://localhost:3000>.
2. Chọn workspace.
3. Vào phần cài đặt của project.
4. Mở **Members**.
5. Chọn role `Admin`, `Member` hoặc `Guest` cho từng thành viên.

Người thực hiện phải là project admin hoặc workspace admin. Nếu không thấy tùy
chọn đổi role, kiểm tra role hiện tại của tài khoản trong project và workspace.

### 13.9. Checklist nghiệm thu yêu cầu

Sau khi triển khai, kiểm tra:

```bash
curl -s http://127.0.0.1:8000/api/instances/ | python -m json.tool | grep -A1 'enable_signup'
docker compose -f docker-compose-local.yml exec api python manage.py shell -c \
  'from plane.db.models import User; from plane.license.models import InstanceAdmin; print("users=", User.objects.count()); print("instance_admins=", InstanceAdmin.objects.count())'
```

Yêu cầu đạt khi:

- `enable_signup` là `false`;
- người chưa được mời không thể tự tạo tài khoản;
- chỉ super admin truy cập được màn hình quản lý thành viên;
- tạo user mới không lưu mật khẩu dạng plain text;
- user bị khóa không thể đăng nhập;
- số lượng user hiển thị khớp database;
- mọi endpoint quản trị đều kiểm tra quyền ở backend;
- database viewer không nhận SQL tùy ý từ trình duyệt;
- có backup trước khi thực hiện thao tác dữ liệu.
- một user có thể có role khác nhau ở từng project;
- project leader có `ProjectMember.role=20`;
- project member thường có role `15`, guest có role `5`;
- leader không thể tự hạ role hoặc chiếm quyền của leader khác trái phép;
- mỗi project luôn có ít nhất một leader active;
- thay đổi role project được kiểm tra ở backend, không chỉ ở frontend.
