# Dokumentacija rešitve za iskanje anomalij in izračun zanesljivosti

## 1. Metode za iskanje anomalij

Sistem uporablja tri-stopenjski postopek detekcije, kjer prve dve metodi služita kot čistilec podatkov za tretjo, naprednejšo metodo.

### Metoda drsečega okna (Sliding Window)
*   **Ničelne vrednosti:** Avtomatsko izločimo vse meritve z vrednostjo 0.
*   **Ravne linije:** Metoda izračuna standardni odklon znotraj drsečega okna. Če je ta bistveno nižji od globalne variance (kar nakazuje na "zmrznjen" senzor ali umetno konstantno vrednost), odsek označimo kot anomalijo.

### Metoda strmih naklonov (Steep Slopes)
*   Metoda identificira lokalne vrhove in doline ter izračuna strmino (naklon) med njimi. 
*   Na podlagi povprečja strmin in standardnega odklona prepoznamo nenadne skoke ali padce, ki so fizikalno nemogoči, in te odseke izločimo.

### Metoda Prophet (Napovedno modeliranje)
*   Z uporabo algoritma **Prophet** modeliramo pričakovano obnašanje meritev. 
*   **Ključna prednost:** Preden podatke podamo modelu Prophet, jih s pomočjo predhodnih metod (Sliding Window in Steep Slopes) očistimo. To modelu omogoča učenje na "čistih" podatkih, s čimer ustvari bolj optimalno napoved. 
*   Anomalije zaznamo kot točke, kjer dejanske meritve močno odstopajo od napovedanih meja modela.

---

## 2. Izračun indeksov zanesljivosti (SAIFI in SAIDI)

Po končani detekciji program združi zaporedne točke z anomalijami v posamezne dogodke prekinitev in izračuna:

*   **SAIFI (System Average Interruption Frequency Index):** Povprečno število prekinitev na lokacijo. Izračuna se kot skupno število vseh dogodkov prekinitev deljeno s številom obdelanih lokacij.
*   **SAIDI (System Average Interruption Duration Index):** Povprečno trajanje prekinitev na lokacijo. Izračuna se kot skupno trajanje vseh prekinitev (v minutah) deljeno s številom obdelanih lokacij.

---

## 3. Navodila za uporabo

1.  V direktorij `vsi_podatki` vstavite svoje `.csv` datoteke z meritvami.
2.  Zaženite program, ki bo samodejno procesiral vse datoteke v mapi.
3.  Program bo v konzoli izpisal izračunane vrednosti SAIFI in SAIDI, podrobno označene anomalije pa shranil v datoteko `rezultati.csv`.

## 4. Rezultati
| Parameter | Vrednost |
| :--- | :--- |
| **Skupno število obdelanih lokacij** (Total sites processed) | 200 |
| **Skupno število dogodkov prekinitev** (Total interruption events) | 10.341 |
| **Skupno trajanje** (Total Duration) | 188.252,00 |
| **SAIFI** | 51,705 |
| **SAIDI** | 941,260 |
