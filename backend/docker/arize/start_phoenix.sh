docker run -d \
  -p 6006:6006 \
  -p 4317:4317 \
  -i -t \
  --name draw-steel-phoenix \
  -v phoenix_data:/mnt/data \
  -e PHOENIX_WORKING_DIR=/mnt/data \
  arizephoenix/phoenix:latest

