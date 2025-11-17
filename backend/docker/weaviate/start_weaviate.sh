if [ "$(docker ps -a -q -f name=draw-steel-weaviate)" ]; then
  docker start draw-steel-weaviate
else
  docker run -d \
    --name draw-steel-weaviate \
    -p 8080:8080 \
    -p 50051:50051 \
    -v weaviate_data:/var/lib/weaviate \
    -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
    cr.weaviate.io/semitechnologies/weaviate:1.34.0
fi