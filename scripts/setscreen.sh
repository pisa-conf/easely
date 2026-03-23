#! /bin/bash


# Nome del file contenente i valori
file="listapi_slideshow.txt"

# Verifica se il file esiste
if [ ! -f "$file" ]; then
    echo "Il file $file non esiste."
    exit 1
fi

# Inizializza l'array per memorizzare i valori
numero=()
schermo=()

# Leggi i valori dal file e memorizzali nell'array
while IFS=" " read -r pinum screen; do
    numero+=("$pinum")
    schermo+=("$screen")
done < "$file"

# Stampa i valori letti dal file
#echo "Valori letti dal file:"
#echo "Prima Colonna (Numero): ${numero[*]}"
#echo "Seconda Colonna (Schermo): ${schermo[*]}"

for ((i=0; i<${#numero[@]}; i++)); do
    x=${numero[i]}
    ip=$((100 + x))
    schermo_corrente=${schermo[i]}
    echo "setting screen on ppm$x the value $schermo_corrente"
    ssh pi@192.168.30.$ip "cd pisameet; cd pisameet; echo \"$schermo_corrente\" > screen.cfg; exit;"
done




