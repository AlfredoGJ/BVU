<?php

include 'Implementacion_APIs.php';

if($_SERVER['REQUEST_METHOD']=='POST')
{
    
    $query= $_POST['query'];
    $resultado=consultaSPARQL($query,"");
    echo $resultado;
    
}


?>



<html >


<head  >

</head>

<body >



    <title> Pruebas SPARQL</title>

    <h1>
        
        Pruebas SPARQL

    </h1>


    <a href="IXD.php" ><p> Investigadores por dependencia</p> </a>
    <form method="POST"   accept-charset="utf-8"  >


        <br>
        Query: 
        <input type="text" name="query" width="200">

        <br>

        
        
       <input type="submit" value="Enviar" >
        
    </form>
   

</body>



</html>