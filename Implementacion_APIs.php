

<?php

function consultaSPARQL($consulta, $formato)
{

    $URL='http://localhost:8080/vivo/api/sparqlUpdate';
    $params= array();
    $params['email']= 'vivo_root@mydomain.edu';
    $params['password']= '123456';
    $params['update']='
    PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
    
    
    INSERT DATA 
    {
       GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> { 
        
        <http://orbis.uaslp.mx/vivo/individual/n70532>
        rdfs:label "Perez Juan "@es-ES.
    
    }}';

    // var_dump($params);
    $curl= curl_init($URL);
    curl_setopt($curl, CURLOPT_POST, 1);
    curl_setopt($curl, CURLOPT_POSTFIELDS,http_build_query( $params) );
    curl_setopt($curl, CURLOPT_RETURNTRANSFER,true);
    curl_setopt($curl, CURLOPT_HTTPHEADER, array('Accept: application/sparql-results+json'));
    // var_dump($curl);
    
    $result=curl_exec ($curl);
    return $result;
}


function leeArchivoConsulta($archivo_consulta)
{

  $texto_consulta='';
  if(!file_exists($archivo_consulta))
  {
    echo 'El archivo de consulta no existe.';
  }
  else
  {
    $fp= fopen($archivo_consulta,'r');
    while(!feof($fp))
    {
      $texto_consulta= $texto_consulta.fgetc($fp);
    }
    fclose($fp);
    return $texto_consulta;
    
  }
}

?>