docker buildx build \
  --platform linux/arm64 \
  -f Dockerfile_netto \
  -t lyngsberg/netto-scraper:latest \
  --push \
  .