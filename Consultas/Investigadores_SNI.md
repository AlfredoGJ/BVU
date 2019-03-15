# Consulta Investigadores SNI
Obtiene los nombres de los investigadores que tienen algun Nivel SNI de una dependencia dada.

## Los nodos involucrados en esta consulta y sus relaciones

(/img/Positions.png)

### 1.  Se obtienen las posiciones de la dependencia y las de la SEP

    Todos los recursos de la clase "Position" que se relacionan con la dependencia
   ``` sparql
    ?Positions a vivo:Position;
             vivo:relates [URI_DEPENDENCIA].
   ```
    Todos los recursos de la clase "Position" relacionados con la URI de la SEP
    ?PositionsSNI a vivo:Position;
                vivo:relates  <http://orbis.uaslp.mx/vivo/individual/n3332>.


### 2.- Se obtienen todos los investigadores relacionados con la dependencia


    # Todas las tripletas en las que la Posicion en la dependencia se relacionen mediante la propiedad "relates"
	?Positions vivo:relates ?Investigador.
    # De las tripletas anteriores, todas aquellas en la que la clase relacionada sea "FacultyMember" 
	?Investigador a vivo:FacultyMember.



### 3.- Se Hace la relacion de los investigadores con las "Positions" de la SEP

    Las tripletas en la que la URI de la SEP se relacione con alguno de los investigadores
    ```sparql
    ?PositionsSNI vivo:relates ?Investigador.
    ```

### 4.- Se vacian el nombre y puesto en las variables que regresará la consulta

    # Se obtiene el nombre del investigador de la propiedad "label"
  	?Investigador rdfs:label ?NombreInvestigador.
    # Se obtiene el nombramiento asignado en la Posicion
    ?PositionsSNI rdfs:label ?Puesto.
			