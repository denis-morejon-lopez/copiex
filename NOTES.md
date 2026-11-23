### Nombre de la aplicación
Copiex 


### Descripción
Copiex es un programa concebido para ejecutar copias de ficheros o directorios dentro de una interfaz Gnome de un sistema operativo Linux.
Está programado en python y tiene como objetivo hacer una gestión eficiente de colas de copias de archivos.


### Requerimientos
1- Programado en Python
2- Al ejecutarse debe quedar como un proceso en la esquina superior derecha del escritorio
3- Allí tendrá un menú contextual para operar sobre él
4- Debes poder seleccionar el fichero origen y luego el destino, utilizando el gestor de archivos de Gnome
5- Las copias deben poder detenerse y reanudarse
6- Las copias deben estar visibles en la ventana principal de la aplicación
7- Cuando está el proceso en ejecución debe poder detectar cuando intento hacer una copia de archivos desde el gestor de ficheros Nautilus
y tomar la copia para sí mismo. En ese momento Nautilus no puede ocuparse de la copia, ni ofrecer el progreso de la misma. Sólo lo hace Copiex.
8- La aplicación debe ser capaz de guardar en tiempo real es estado de cada copia activa en el historial de copias. De forma que si se apaga
accidentalmente la aplicación quede en algún fichero o base de datos local el estado de la copia, y restaurarla automáticamente en cuando
las condiciones lo propicien. Estas condiciones son:
- Dispositivo origen listo
- Fichero origen presente
- Dispositivo destino listo
- Fichero destino presente de forma incompleta, o inexistente 
9- Cuando una copia termine debe emitir una alerta audible, y debe aparecer en lugar del botón "Cancelar", un botón nombrado "Eliminar" para quitar la operación de la pantalla.
10- En el menú de la aplicación debe haber una opción "Acerca de" donde aparezca una ventana con la descripción reducida de lo que hace la aplicación y la versión de la misma. 
esa descripción debe existir en un fichero texto nombrado menu.yaml
11- El fichero nombrado menu.yaml contendrá los nombres de las opciones de  menu. Y si una opción de menu deriva en una ventana emergente, el texto de esa ventana debe estar
reflejado en ese fichero menu.yaml
12- Necesitamos que copiex también pueda copiar hacia o desde dispositivos mtp://
13- La interfaz debe poder cambiar entre español e inglés desde el menú, incluidos los textos de Copiex en Nautilus.
14- Al instalar el .deb, la aplicación debe tomar el idioma de la interfaz Gnome: español si Gnome
está en español e inglés si está en cualquier otro idioma. Después el usuario lo puede cambiar
desde el menú, como ya funciona.
15- El tiempo estimado de culminación de una copia debe ser realista y no debe cambiar
continuamente: debe basarse en el ritmo reciente de la copia y la cifra mostrada debe quedar
estable mientras no haya un cambio significativo.
16- Al usar «Cortar con Copiex» y «Pegar con Copiex» con origen y destino en el mismo
dispositivo de almacenamiento y partición, la operación debe ser inmediata: basta con mover
la referencia del fichero o directorio al nuevo camino, sin copiar los datos. Solo cuando
el destino esté en otra partición (o sea MTP) debe copiar y después borrar el origen.

### Errores detectados


### Estado de implementación (23/11/2026)

Los 16 requerimientos y los 4 errores están resueltos y probados. El 16/11 se añadieron el
requerimiento 12 (copiar hacia/desde `mtp://`), «Cortar con Copiex» (mueve: copia y borra
los orígenes al terminar, también con «Pegar con Copiex N destinos») y el icono a color en
la bandeja (la «C» blanca sobre verde). El 17/11 se añadió el requerimiento 13: selector de
idioma español/inglés en el menú del Centinela y de la ventana, con preferencia guardada en
`~/.config/copiex/language` y etiquetas de Nautilus que cambian sin reiniciar (al abrir el
menú de nuevo). El 18/11 se añadió el requerimiento 14: el `postinst` del `.deb` escribe el
idioma inicial de cada usuario según la interfaz GNOME (español si está en español, inglés
en cualquier otro caso) sin pisar una elección previa. El 18/11 se añadió además el
diálogo «Destinos de la copia» al botón «Nueva copia» de la ventana: permite repartir una
copia a varias carpetas sin pasar por Nautilus. El detalle técnico, las pruebas y el
estado exacto al cerrar la sesión están en `TODO.md`; las reglas de trabajo, en `AGENTS.md`.

«Cortar con Copiex» y el cambio de idioma en el menú real de Nautilus están confirmados por
el usuario (17/11). Queda solo confirmar que el icono del panel es el verde. El código,
`menu.yaml` y la documentación se commitearon primero en `ff317f2`; el empaquetado,
`upgrade.sh`, `.gitignore` y la retirada de `install.sh` se publicaron después en
**`ce8d9ee`** (`repo-copiex/main`). El 17/11 se publicó en **`09fb53f`** el arreglo de
reanudación de copias recuperadas y, después, en **`fc04da6`** «Idioma inglés», el selector
de idioma. El aviso a Nautilus (`emit_items_updated_signal()` al cambiar de idioma), el
idioma inicial del `.deb`, esta documentación y el diálogo de destinos del botón «Nueva copia» se publicaron juntos en el commit del 18/11
**`cca1b2c`** («Varios destinos desde la ventana principal»), que dejó el árbol limpio.
Desde entonces los `__pycache__/*.pyc` ya no se versionan. El 23/11 se añadió el
requerimiento 15: el tiempo restante se calcula con la velocidad de los últimos 15 s y solo
cambia cuando la diferencia es significativa, para que no oscile en la ventana
(`copiex/engine.py`; detalle en la sección 3 quinvices de `TODO.md`). También el 23/11 se
añadió el requerimiento 16: «Cortar con Copiex» dentro de la misma partición ya no copia,
renombra (movimiento instantáneo) y deja la copia y borrado para otra partición, MTP,
varios destinos o un nombre ya ocupado (sección 3 sexvicies de `TODO.md`).

El 23/11 se publicó además lo que quedaba sin push: **`26a6873`** «Publicar el icono de la
bandeja como mapa de bits» y **`273ae03`** «Copiex 1.0.1: mover dentro de la misma
partición y arreglar el empaquetado». La **licencia del proyecto es GPL-3.0**: el usuario
añadió `LICENSE` desde la web de GitHub en **`517b76e`**, entró con `git pull`
(fast-forward) y ya está en `repo-copiex/main`; el árbol queda limpio (sección
3 septvicies de `TODO.md`).

Desde el 16/11 hay un instalador `.deb` en la raíz del proyecto
(`copiex_1.0.1_amd64.deb`, generado con `packaging/build-deb.sh`). Incluye las
dependencias en un repositorio APT local para instalar sin Internet y, si hay red y
terminal, pregunta si actualizarlas desde Ubuntu. `install.sh` ya no existe: el `.deb`
instala la aplicación y `./upgrade.sh` actualiza las dependencias (directas y transitivas
instaladas), reconstruye el paquete con las versiones actuales y reinstala Copiex. El
`.deb` y las carpetas de construcción están en `.gitignore` y no se versionan. No se debe
hacer commit ni push sin pedirlo.
