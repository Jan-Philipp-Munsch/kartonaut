# Klick für Klick: eine offene Verbindung in KiCad schließen

Diese Anleitung erklärt jeden einzelnen Klick am Beispiel, das am 23.10.2026 so gemacht wurde:
**C6 Pad 2 (Netz GND_PWR) bekommt ein Via auf die GND_PWR-Fläche der Unterseite.**
Die Liste aller Stellen steht in `HANDROUTING.md`. Hier geht es nur um das *Wie*.

Wörter, die immer wieder vorkommen:

- **Pad**: die Kupferfläche eines Bauteils, an die gelötet wird.
- **Bahn** (Leiterbahn): ein Kupferstreifen zwischen zwei Punkten.
- **Via**: ein kleines durchkontaktiertes Loch. Es verbindet die Lagen miteinander.
- **Lage**: die Platine hat vier Kupferschichten. F.Cu oben (rot), In1.Cu (GND-Fläche),
  In2.Cu (Signale), B.Cu unten (Versorgungsflächen).
- **Fläche** (Zone): großes Kupferstück, das KiCad selbst ausfüllt, um alles andere herum.
- **Netz**: alles, was elektrisch verbunden sein soll, z. B. GND_PWR.

---

## Teil A: Einmal vorbereiten (pro Sitzung)

**A1. Den Leiterplatteneditor öffnen.**
Doppelklick auf das Projekt `mainboard.kicad_pro` im Worktree-Ordner
`.claude\worktrees\rev-b1\hardware\mainboard\kicad`. Es öffnet sich die KiCad-Projektverwaltung.
Dort ein Klick auf **Leiterplatteneditor** (das grüne Platinensymbol, dritte Zeile).
*Warum:* Nur der Worktree-Ordner hat den Stand rev B1. Der Ordner `hardware\mainboard\kicad` direkt im
Repository ist noch rev B. Kommt die Warnung „Datei offen“, ist das Projekt schon in einem anderen
Fenster offen: **Abbrechen** klicken und das andere Fenster benutzen.

**A2. Raster fein stellen.**
Oben in der zweiten Werkzeugleiste steht ein Feld mit z. B. „0,5000 mm“. Ein Klick darauf öffnet eine Liste.
Klick auf **0,0250 mm** (oder 0,0500 mm).
*Warum:* Die Pads sind nur 0,25 bis 1 mm groß. Bei 0,5 mm Raster springt der Mauszeiger zu grob.

**A3. Router auf „Schieben“ prüfen.**
Menü **Route** (oben, sechster Eintrag) → ganz unten **Interaktiven Router einstellen…**.
Im Dialog links muss **Schieben** markiert sein. Klick auf **OK**.
*Warum:* „Schieben“ drückt fremde Bahnen beiseite, wenn die neue Bahn nicht durchpasst.
„Kollisionen hervorheben“ würde nur rot anzeigen und nichts schieben.

**A4. Breiten aus der Netzklasse.**
Links oben in der zweiten Werkzeugleiste müssen die zwei Felder
**„Leiterbahn: Netzklassenbreite verwenden“** und **„Via: Netzklassengrößen verwenden“** zeigen.
Falls nicht: Feld anklicken, diesen Eintrag wählen.
*Warum:* Dann nimmt KiCad automatisch 1,0 mm für Strom, 0,8 mm für GND_PWR und 0,2 mm für Signale.

**A5. Die Arbeitsliste öffnen.**
Menü **Inspektion** → **Designregeln überprüfen (DRC)**. Im Dialog unten rechts **DRC starten** klicken.
Nach ein paar Sekunden oben auf den Reiter **Unverbundene Elemente** klicken.
*Warum:* Diese Liste ist das, was noch fehlt. Jeder Eintrag hat zwei Zeilen: die beiden Enden,
die verbunden werden müssen. Den Dialog kann man an der rechten unteren Ecke größer ziehen.

---

## Teil B: Zur Stelle navigieren

**B1. Ganze Platine zeigen.** Mauszeiger irgendwo auf die Platine, Taste **Pos1** (Home).

**B2. Hineinzoomen, und zwar richtig.**
Das Mausrad zoomt. **Wichtig:** KiCad schiebt bei jedem Zoomschritt die Stelle unter dem Mauszeiger
in die Bildmitte. Deshalb so vorgehen:
1. Mauszeiger genau auf die Stelle setzen (hier C6, links unten neben dem Teensy-Sockel).
2. **Einen** Schritt mit dem Mausrad nach vorn drehen. Die Stelle springt in die Bildmitte.
3. Mauszeiger jetzt in die **Bildmitte** setzen und weiter drehen, bis die Pads groß sind
   (Zoom etwa 20, steht unten in der Statusleiste als „Z 20,80“).

Dreht man das Rad mehrmals, ohne den Zeiger nachzuführen, wandert die Ansicht von der Stelle weg.

**B3. Kontrolle mit den Koordinaten.**
Unten in der Statusleiste stehen **X** und **Y** des Mauszeigers in mm. Für C6 Pad 2 ist das
X 117,58 / Y 141,75. Mit dem Zeiger über das Pad fahren und vergleichen.

Alternativ: im DRC-Dialog auf eine Zeile **doppelklicken**. KiCad springt dann zu diesem Element
und markiert es.

---

## Teil C: Die Verbindung ziehen (Beispiel C6, Via auf GND_PWR)

Vorher geklärt (mit dem Skript, das kannst du dir sparen): Unter C6 liegt auf der Unterseite B.Cu die
GND_PWR-Fläche. 1,3 mm rechts von Pad 2, bei X 118,90 / Y 141,75, ist auf allen vier Lagen genug Platz
für ein Via. Darum: kurze Bahn vom Pad nach rechts, dort ein Via.

**C1. Router-Werkzeug holen.**
Menü **Route** → **Einzelne Leiterbahn routen**.
*Woran man es sieht:* Rechts in der senkrechten Werkzeugleiste ist das Routing-Symbol blau hinterlegt,
der Mauszeiger ist ein Fadenkreuz. Die Taste **X** macht dasselbe.

**C2. Am Pad anfangen.**
Ein Linksklick mitten auf **Pad 2 von C6** (beschriftet „2 GND_PWR“).
*Was passiert:* Alles, was nicht zu GND_PWR gehört, wird dunkel. Am Pad hängt jetzt eine rote Bahn,
die dem Mauszeiger folgt. Unten links steht „Route Leiterbahn: GND_PWR“ und die Breite 0,8 mm
„aus Netzklasse Rueckstrom“. Damit weißt du: richtiges Netz, richtige Breite.

**C3. Zum Via-Punkt fahren, nicht klicken.**
Maus nach rechts bewegen, bis die Statusleiste X 118,90 / Y 141,75 zeigt.
*Warum nicht klicken:* Ein Klick würde hier eine Ecke der Bahn festlegen. Das Via soll aber
genau an das Ende.

**C4. Via anhängen.**
Taste **V** drücken (nicht klicken). Am Bahnende erscheint ein Kreis: das Via.
Einmal die Maus minimal bewegen, damit KiCad neu zeichnet.
*Woran man sieht, dass es passt:* Das Via ist hell und nicht rot umrandet. Rot heißt: zu nah an
etwas anderem. Dann die Maus ein Stück verschieben, bis es hell wird.

**C5. Festklicken.**
Ein Linksklick. Bahn und Via sind gesetzt. Der Router würde jetzt auf der anderen Lage weitermachen.

**C6. Fertig mit dieser Bahn.**
Einmal **Esc**: die Bahn endet am Via. Noch einmal **Esc**: das Router-Werkzeug wird abgelegt.
*Warum zweimal:* Das erste Esc beendet nur die laufende Bahn, das zweite wechselt zurück zum Auswählen.

**C7. Flächen neu füllen.**
Maus auf die Platine, Taste **B**.
*Warum:* Die Flächen werden nicht von selbst neu berechnet. Erst nach **B** fließt die GND_PWR-Fläche
an das neue Via heran, und die anderen Flächen machen ihm Platz. Ohne **B** meldet der DRC
„Freiraum-Verstoß“ und die Verbindung als offen.

**C8. Speichern.**
**Strg+S**. Im Fenstertitel verschwindet das Sternchen vor „mainboard“.

**C9. Prüfen.**
Im DRC-Dialog **DRC starten**. Unten in der Statusleiste steht „Ungeroutet“: die Zahl ist um eins kleiner.
Im Reiter „Verstöße“ dürfen keine neuen roten Fehler stehen.

Wenn etwas schiefging: **Strg+Z** nimmt den letzten Schritt zurück. Mehrmals drücken geht auch.

---

## Teil D: Die anderen Arten von Stellen

**D1. Pad an Bahn auf derselben Lage (z. B. SEL2, MOT_A).**
Wie Teil C, aber ohne **V**: am Pad anfangen (C2), zum Ende der anderen Bahn fahren und
**dort klicken**. KiCad rastet am Bahnende ein und beendet die Bahn selbst.
Klappt es nicht auf direktem Weg, Zwischenpunkte setzen: jeder Linksklick ist eine Ecke.

**D2. Über eine andere Lage (z. B. CS_EXT0, VBAT1_SENSE).**
Am Pad anfangen, ein kurzes Stück herausfahren, **V** drücken und klicken: jetzt ist man auf der
anderen Lage (oben im Lagenfeld steht dann In2.Cu oder B.Cu). Weiterfahren bis zum Ziel. Kurz vor dem Ziel
wieder **V** und klicken, dann auf das Ziel-Pad klicken.
Welche Lage nach dem Via kommt, steht im Lagenfeld oben (z. B. „F.Cu (PgUp)“). Mit **Bild hoch** und
**Bild runter** wechselt man vor dem Klick die Lage.

**D3. Stromnetze (VSERVO, VBAT2_*, VBAT_PROT, PYRO*_NEG).**
Nur auf F.Cu, **niemals V drücken**. Breite kommt aus der Netzklasse (1,0 mm).
Ist es an einem kleinen Pad zu eng, mit **W** auf eine schmalere Breite aus der Liste schalten.

**D4. Bauteil ein Stück verschieben, wenn kein Weg frei ist.**
Mauszeiger auf das Bauteil (nicht auf eine Bahn), Taste **M**, Maus bewegen, Linksklick.
Die angeschlossenen Bahnen reißen dabei ab. Danach jede Bahn mit **D** (Bahn ziehen) wieder
an das Pad heranziehen: Zeiger auf das Bahnende, **D**, zum Pad, Linksklick.
Nur für C36, C37, C38, R26 und JP2 vorgesehen, und nur 0,5 bis 1 mm.

---

## Was man nie tun darf

- `./make.sh pcb` oder `gen_pcb.py place` ausführen: das erzeugt die Platine neu und löscht alle Handarbeit.
- Ein Via in den 5-mm-Kreis um die IMU U4 (X 127,0 / Y 109,5) setzen.
- Etwas an ISENS_P oder ISENS_N anhängen.
- Im Fenster mit dem Hauptordner-Projekt arbeiten (`hardware\mainboard\kicad` ohne `.claude\worktrees`).
