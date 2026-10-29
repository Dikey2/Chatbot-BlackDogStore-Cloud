#!/usr/bin/env bash
# Campaña completa del 80 % contra Docker Compose LOCAL (nunca contra Render).
#   Modalidad A: 1000, 2000, 3000 y 5000 solicitudes totales (50 usuarios).
#   Modalidad B: 50, 100, 200, 300 y 500 usuarios concurrentes durante 60 s.
# Lectura y escritura se ejecutan por separado. En B, si un nivel supera 5 % de
# fallos o 5 s de mediana, no se ejecutan los niveles superiores de ese perfil.
# Los rate limits se suben al empezar y se restauran SIEMPRE al terminar.
set -uo pipefail
cd "$(dirname "$0")/.."
trap 'loadtest/limites.sh normales' EXIT
loadtest/limites.sh altos

READ="Lectura LecturaAsesor"
WRITE="Escritura"

# Fallos (%) y mediana (ms) del último escenario ejecutado con ese nombre.
check() {
  local file
  file=$(ls -t loadtest/resultados/*_"$1"_consola.txt | head -1)
  grep -m1 Aggregated "$file" | awk '{gsub(/[()%]/, " "); print $4, $9}'
}

for total in 1000 2000 3000 5000; do
  for profile in lectura escritura; do
    classes=$READ; [ $profile = escritura ] && classes=$WRITE
    TOTAL_REQUESTS=$total loadtest/ejecutar.sh "A-${total}req-${profile}" "$classes" 50 10 15m
    sleep 20
  done
done

for profile in lectura escritura; do
  classes=$READ; [ $profile = escritura ] && classes=$WRITE
  for users in 50 100 200 300 500; do
    name="B-${users}u-${profile}"
    TOTAL_REQUESTS=0 loadtest/ejecutar.sh "$name" "$classes" "$users" $((users / 10)) 60s
    read -r fail median <<<"$(check "$name")"
    echo "   -> fallos=${fail}% mediana=${median}ms"
    if awk -v f="$fail" -v m="$median" 'BEGIN { exit !(f > 5 || m > 5000) }'; then
      echo "   -> se detiene el escalamiento de $profile: el entorno local llegó a su límite"
      break
    fi
    sleep 20
  done
done
