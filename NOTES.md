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

### Errores detectados
1- Copiex no detecta la copia que se intenta hacer a través de Nautilus cuando ya está activo en la ventana superior derecha.
2- Cuando la conexión con el origen o con el destino falla, saca un error de entrada/salida, pero no se reanuda automáticamente la copia cuando se restablecen los dispositivos. Tampoco en ese
momento de desconexión aparece algún botón para cancelar la copia si se quisiera.
3- Veo cuando copio varios ficheros se hacen muy lentas las copias. Debe mejorar el algoritmo de copia para minimizar el tiempo total de copia.
4- Cuando Copiex no está en ejecución, y doy clic derecho sobre un archivo y selecciono:  "Copiar con Copiex". Y luego en el dispositivo destino doy clic derecho "¨Pegar con Copiex"
no veo que active e inicie la aplicación, y debería hacerlo.
