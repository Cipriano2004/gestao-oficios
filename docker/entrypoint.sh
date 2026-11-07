#!/bin/sh
# Aguarda o banco, aplica as migrações e inicia o sistema.
set -e

tentativas=0
until flask db upgrade; do
  tentativas=$((tentativas + 1))
  if [ "$tentativas" -ge 30 ]; then
    echo "Banco de dados indisponível após 30 tentativas." >&2
    exit 1
  fi
  echo "Aguardando o banco de dados... ($tentativas/30)"
  sleep 2
done

exec "$@"
