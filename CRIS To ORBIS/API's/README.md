# CRIS-To-ORBIS
Es el modulo encargado de la transferencia de datos del sistema CRIS a la plataforma ORBIS, está basado en el uso de dos herramientas: la API **SarqlUpdate** y el modulo **d2r-Query** del software D2R-Server.

A continuación se describe la estructura, funciones y parámetros del archivo  _cristoorbis.pm_ que es donde se implementa este modulo.

## Estructura
Se divide en 3 secciones:
* Parámetros. 
* Funciones de datos.
* Funciones de lógica de transacción y llamada a las API's
## Parámetros

```perl
# Parametros D2R
my $D2R_PATH="/d2rq-0.8.1/d2r-query";
my $D2R_MAPPING_FILE_PATH="/d2rq-0.8.1/CRIS_Mapping.ttl";
my $D2R_BASE_URI="http://localhost:2020";

# Parametros VIVO
my $VIVO_API_URL="http://localhost:8080/vivo-193-blank/api/sparqlUpdate";
my $VIVO_EMAIL="vivo_api\@bvu.edu";
my $VIVO_PASSWORD="helloapi";
```
**D2R_PATH** : Ruta absoluta de el ejecutable d2r-query, este se encuentra en la carpeta de instalación de d2r-Server.

**D2R_MAPPING_FILE_PATH** : Ruta absoluta de el archivo de mapeo, no necesariamente tiene que estar en la carpeta de instalación de d2r.

**D2R_BASE_URI** :URI base para todos los objetos que se generen en el mapeo, a diferencia de la constante definida en el archivo de mapeo, esta no lleva diagonal  "/"  al final.

**VIVO_API_URL** : URL usada para hacer las llamadas a la API SparqlUpdate, y es igual a la URL de VIVO más "/api/sparqlUpdate".

**VIVO_API_URL** : E-mail de la cuenta de VIVO.

**VIVO_API_URL** : Contraseña de la cuenta de VIVO.

## Funciones de datos
Son funciones usadas para insertar o eliminar ciertos datos en especifico y  que están relacionados entre si en una sola llamada a las API's.

### UpdateVcard( )
Actualiza el objeto VCard del investigador, solo tendra efecto con los investigadores que tengan "activo" en la columna **status1** y "aceptado" en **status2** en la tabla investigador.

 **Tablas usadas:** 
investigador, scopus, orcid, wos, googlescholar, researchgate, publons, otrosperfilesweb.


### UpdatePropiedades( )

 Esta función se tiene que llamar siempre que se actualice información del investigador o se cambie la relación de este con algún otro elemento p. Ej: cambió el correo electrónico, teléfono o se agrega o se elimina una publicación, curso, conferencia, etc.
 
 **Tablas usadas:** 
investigador.


### UpdatePositions( )

 Actualiza todos los objetos Position relacionados con el investigador y las organizaciones asociadas a estos.
 
 **Tablas usadas:** 
positions, organizaciones.



## Funciones de lógica de transacción y llamada a las API's
Son las funciones que trabajan directamente con las API's o que manejan el flujo de información entre ellas.

### D2RAskQuery( )
Hace una consulta SPARQL a D2R.
 **Parámetros:**
* Texto de la consulta Sparql

**Regresa:**
* Texto en formato .ttl con los datos requeridos por la consulta

```perl
sub D2RAskQuery
{
    # Armado de las partes del comando para ejecutar la consulta
    my $query = $_[0];

    # print $cgi->header('text/json');
    # print $query;

    # Se ejecuta el comando con la consulta
    my $result = `$D2R_PATH -f ttl  $D2R_MAPPING_FILE_PATH $query`;
    # print $result;
    # Se procesa el resultado para eliminar los prefijos: @prefix: <uri>.
    my @lines = split(/\n/,$result);
    my $ttl_data ="";
    foreach my $line(@lines)
    {
        if(!($line=~/^\@prefix/))
        {
            $ttl_data.=$line."\n";
        }
    }
    return $ttl_data;
}
```
### vivo_data_update( )
 Realiza eliminación e insercion de datos en VIVO usando la API SparqlUpdate
**Parametros:**
* Texto en formato .ttl con la informacion a insertar o eliminar.
* 'insert' o 'delete' para especificar la accion a realizar, no importan mayusculas o minusculas.
 
 **Regresa:**
* 1 si la modificacion es correcta, 0 si ocurrió algun error.

```perl
sub vivo_data_update
{

    my $data = $_[0];
    my $query= '
    PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
    prefix owl:     <http://www.w3.org/2002/07/owl#>
    prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    prefix uaslp:   <http://orbis.uaslp.mx/vivo/ontology/uaslp#>
    prefix xsd:     <http://www.w3.org/2001/XMLSchema#>
    prefix vocab:   <http://localhost:2020/vocab/>
    prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
    prefix vivo:    <http://vivoweb.org/ontology/core#>
    prefix map:     <http://localhost:2020/#>
    prefix vitro:   <http://vitro.mannlib.cornell.edu/ns/vitro/0.7#>
    prefix db:      <http://localhost:2020/>
    prefix foaf:    <http://xmlns.com/foaf/0.1/>
    PREFIX vcard:    <http://www.w3.org/2006/vcard/ns#>
    PREFIX obo:      <http://purl.obolibrary.org/obo/>
    PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
    PREFIX bibo:     <http://purl.org/ontology/bibo/>
    PREFIX scires:   <http://vivoweb.org/ontology/scientific-research#>
    PREFIX event:   <http://purl.org/NET/c4dm/event.owl#>

    '.$_[1].' DATA
    {
       GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> {'

       .$data.

    '}}';
    #print $query;

    my $params= 'email='.$VIVO_EMAIL.'&password='.$VIVO_PASSWORD.'&update='.$query;
    # print $params;
    my $curl = WWW::Curl::Easy->new;
    $curl->setopt(WWW::Curl::Easy::CURLOPT_URL, $VIVO_API_URL);
    $curl->setopt(WWW::Curl::Easy::CURLOPT_POST,1);
    $curl->setopt(WWW::Curl::Easy::CURLOPT_HTTPHEADER,['Accept: application/sparql-results+json']);
    $curl->setopt(WWW::Curl::Easy::CURLOPT_POSTFIELDS,$params);
    
    my $response = $curl->perform;
    my $resp_code= $curl->getinfo(WWW::Curl::Easy::CURLINFO_HTTP_CODE);

    if($response==0)
    {
        if($resp_code eq 200)
        {
            print "Información modificada exitosamente";
            return 1;
        }

        if($resp_code eq 403)
        {
            print "Ocurrio un problema de autentificación";
            return 0;
        }

        if($resp_code eq 400)
        {
            print "Los datos tienen un formato erroneo";
            return 0;
        }
    }
    else
    {
        #print("Ocurrio un error con CURL: $response ".$curl->strerror($response)." ".$curl->errbuf."\n");
        return 0;
    }
}

```

### GeneralTransaction( )

 Funcion que realiza la operacion de transaccion de datos entre D2R y la API de VIVO
 **Recibe:**
 * Consulta para obtener los datos de la transaccion
 * Tipo de transaccion a realizar, puede ser: 'update', 'delete', 'insert'

```perl
sub GeneralTransaction
{
    # se piden los datos a D2R
    my $result = D2RAskQuery($_[0]);
    # Se checa si se obtuvieron datos
    if($result ne "")
    {
        print $result;
        # Se hace la transaccion con VIVO (insercion eliminacion o actualizacion)
        if(VivoAPITransaction($result, $_[1]))
        {
            print "\nTransaccion completa\n";
        }else{
            print "\nFalla en transaccion\n";
        }

    }else{
        printf ("\nNo se encontraron datos para '%s' ",$_[0]);
    }
}
```

### VivoAPITransaction( )

 Función que maneja la lógica de la transacción de datos con la API de VIVO para las distintas opciones
 **Recibe:**
 * Los datos en formato .TTL
 * Tipo de transaccion a realizar, puede ser: 'update', 'delete', 'insert'
 
 **Regresa:**
 * 1 si se realizó correctamente la transacción.
 * 0 hubo un error durante la transacción.
```perl
sub VivoAPITransaction
{
    my $result = 0;
    if($_[1] eq 'update')
    {
        $result=vivo_data_update($_[0], "DELETE");
        $result=vivo_data_update($_[0], "INSERT");

    }
    if($_[1] eq 'insert')
    {
        $result=vivo_data_update($_[0], "INSERT");

    }
    if($_[1] eq 'delete')
    {
        $result=vivo_data_update($_[0], "DELETE");

    }
    return $result;

}
```











    

