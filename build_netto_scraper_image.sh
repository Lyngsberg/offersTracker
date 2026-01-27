docker buildx build \
  --platform linux/arm64 \
  -f Dockerfile_netto_scraper \
  -t lyngsberg/netto-scraper:latest \
  --push \
  .