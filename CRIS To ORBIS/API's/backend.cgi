#!/usr/bin/perl
# use strict;
use warnings;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use utf8;
use CGI qw(-utf8);
use DBI;
use Encode;
use LWP::UserAgent;
use HTTP::Request;
use JSON::PP qw(encode_json decode_json);
use WWW::Curl::Easy;
my $cgi = new CGI;

my $idInvestigador = $cgi->param("ID");


# Parametros D2R
my $D2R_PATH="/d2rq-0.8.1/d2r-query";
my $D2R_MAPPING_FILE_PATH="/d2rq-0.8.1/CRIS_Mapping.ttl";
my $D2R_BASE_URI="http://localhost:2020";

# Parametros VIVO
my $VIVO_API_URL="http://localhost:8080/vivo-193-blank/api/sparqlUpdate";
my $VIVO_EMAIL="vivo_api\@bvu.edu";
my $VIVO_PASSWORD="helloapi";



# Tablas: investigador, scopus, orcid, wos, googlescholar, researchgate, publons, otrosperfilesweb
sub UpdateVcard
{
    my $query= "\"
    DESCRIBE ?vcard ?email ?name ?url ?telephone ?title ?address
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        
        OPTIONAL{?Investigador uaslp:crisEstatus1 ?estatus1.}
        OPTIONAL{?Investigador uaslp:crisEstatus2 ?estatus2.}

        BIND
        (
            IF(STR(?estatus1)='activo'&& STR(?estatus2)='aceptado',?Investigador ,'') AS ?Inv
        )
        
    
        ?Inv obo:ARG_2000028 ?vcard.
        OPTIONAL{?vcard vcard:hasName ?name.}
        OPTIONAL{?vcard vcard:hasEmail ?email.}
        OPTIONAL{?vcard vcard:hasURL ?url.}
        OPTIONAL{?vcard vcard:hasTelephone ?telephone.}
        OPTIONAL{?vcard vcard:hasTitle ?title.}
        OPTIONAL{?vcard vcard:hasAddress ?address.}
    }\"";
    GeneralTransaction($query,$_[1]);
}

# Esta funcion se tiene que llamar siempre que se
# actualice información del investigador o se cambie
# la relación de este con algun otro elemento
# p. Ej: cambió el correo electrónico, telefono o se agrega
# o se elimina una publicación, curso, conferencia, etc.
sub UpdatePropiedades
{
    my $query= "\"DESCRIBE ?Inv
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        OPTIONAL{?Investigador uaslp:crisEstatus1 ?estatus1.}
        OPTIONAL{?Investigador uaslp:crisEstatus2 ?estatus2.}

        BIND
        (
            IF(STR(?estatus1)='activo'&& STR(?estatus2)='aceptado',?Investigador ,'') AS ?Inv
        )
    }\"";

    GeneralTransaction($query,$_[1]);
}

# Tablas: positions
sub UpdatePositions
{

    my $query= "\"
    DESCRIBE  ?Positions ?positionOrg
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).

        

        ?Investigador vivo:relatedBy ?Positions.

        # Positions
        ?Positions a vivo:Position.
        OPTIONAL{?Positions vivo:relates ?positionOrg.}

    }\"";
    GeneralTransaction($query,$_[1]);

}
# Tablas: areasinvestigacionfromvivo, areasporinvestigador
sub UpdateResearchAreas
{

    my $query=  "\"DESCRIBE ?AreasInvestigacion
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).

        ?Investigador vivo:hasResearchArea ?AreasInvestigacion.
    }\"";
    GeneralTransaction($query,$_[1]);


}

# Tablas: investigador
sub UpdateGeographicFocus
{

    my $query=  "\"DESCRIBE ?GeographicFocus
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador vivo:geographicFocus ?GeographicFocus.
    }\"";
    GeneralTransaction($query,$_[1]);


}

# Funcion que realiza la operacion de transaccion de datos entre D2R y la API
# de VIVO
# Rcibe:
# * Consulta para obtener los datos de la transaccion
# * Tipo de transaccion a realizar, puede ser: 'update', 'delete', 'insert'
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


# Función que maneja la lógica de la transacción de datos con la API de VIVO
# para las distintas opciones
# Recibe:
# * los datos en formato .TTL
# * Tipo de transaccion a realizar, puede ser: 'update', 'delete', 'insert'
# Regresa:
# 1 si se realizó correctamente la transaccion
# 0 hubo un error durante la transacción
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

# Función que actualiza todos los datos de una publicación, ya sea que
# sean datos propios de la publicación o de objetos relacionados con ella
# como conferencias, publishers, Grants o incluso otras publicaciones
# solo usar cuando se requiera actualizar los datos de una publicacion
sub UpdatePublicacion
{
    my $query ="\"
    DESCRIBE
    ?Document
    ?Source
    ?Publisher
    ?Status
    ?Access
    ?Conference
    ?Date
    ?Funding
    ?SubjectArea
    ?Cites
    ?CitedBy
    WHERE
    {
        
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Doc).
        OPTIONAL{?Doc uaslp:crisEstatus1 ?estatus1.}
        OPTIONAL{?Doc uaslp:crisEstatus2 ?estatus2.}

        BIND
        (
            IF(STR(?estatus1)='activo'&& STR(?estatus2)='aceptado',?Doc ,'') AS ?Document
        )

        OPTIONAL{ ?Document vivo:hasPublicationVenue ?Source. }
        OPTIONAL{ ?Document vivo:publisher ?Publisher.}
        OPTIONAL{ ?Document bibo:status ?Status.}
        OPTIONAL{ ?Document scires:documentationFor ?Access}
        OPTIONAL{ ?Document bibo:presentedAt ?Conference. }
        OPTIONAL{ ?Document vivo:dateTimeValue ?Date. }
        OPTIONAL{ ?Date vivo:dateTimeValue ?Date. }
        OPTIONAL{ ?Document vivo:hasFundingVehicle ?Funding. }
        OPTIONAL{ ?Document vivo:hasSubjectArea ?SubjectArea. }
        OPTIONAL{ ?Document bibo:cites ?Cites. }
        OPTIONAL{ ?Document bibo:citedBy ?CitedBy. }


    }\"";
    GeneralTransaction($query,$_[1]);

}


# Tablas: leaderof, organizaciones
sub UpdateHeadOf
{
    my $query = "\"
    DESCRIBE
    ?leaderRole
    ?leaderRoleInterval
    ?leaderRoleStart
    ?leaderRoleOrg
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?leaderRole.

        ?leaderRole a vivo:LeaderRole.
        OPTIONAL{?leaderRole vivo:roleContributesTo ?leaderRoleOrg.}
        OPTIONAL{
        ?leaderRole  vivo:dateTimeInterval ?leaderRoleInterval.
        ?leaderRoleInterval vivo:start ?leaderRoleStart.
        ?leaderRoleInterval vivo:end ?leaderRoleEnd.}
    }\"";
    GeneralTransaction($query,$_[1]);
}


# Tablas: membersof, organizaciones, catalogoca
sub UpdateMemberOf
{
    my $query = "\"
    DESCRIBE
    ?memberRole
    ?memberRoleInterval
    ?memberRoleStart
    ?memberRoleOrg

    WHERE
    {
       BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?memberRole.


        ?memberRole a vivo:MemberRole.
        OPTIONAL{?memberRole vivo:roleContributesTo ?memberRoleOrg.}
        OPTIONAL{
        ?memberRole  vivo:dateTimeInterval ?memberRoleInterval.
        ?memberRoleInterval vivo:start ?memberRoleStart.
        ?memberRoleInterval vivo:end ?memberRoleEnd.}
    }\"";

    GeneralTransaction($query,$_[1]);
}


# Tablas: eventosxinvestigador, catalogoeventos, catalogocongresos
sub UpdateAttendedAndOrganizedEvent
{
    my $query = "\"
    DESCRIBE
    ?attendeeRole
    ?attendedEvent
    ?attendeeRoleInterval
    ?attendeeRoleStart
    ?attendeeRoleEnd

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).

        ?Investigador obo:RO_0000053 ?attendeeRole.



        {?attendeeRole a vivo:AttendeeRole.}
         UNION
        {
            ?attendeeRole a vivo:OrganizerRole.

        }
        OPTIONAL{
            ?attendeeRole vivo:dateTimeInterval ?attendeeRoleInterval.
            ?attendeeRoleInterval vivo:start ?attendeeRoleStart.
            ?attendeeRoleInterval vivo:end ?attendeeRoleEnd.
        }
        OPTIONAL{?attendeeRole  obo:BFO_0000054 ?attendedEvent.}

    }\"";
    GeneralTransaction($query,$_[1]);


}



sub UpdatePublications
{

    my $query= "\"
    DESCRIBE
    ?Publications
    ?Document
    ?Source
    ?Publisher
    ?Status
    ?Access
    ?Conference
    ?Date
    ?Funding
    ?SubjectArea
    ?Cites
    ?CitedBy

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador vivo:relatedBy ?Publications.

        ?Publications a vivo:Authorship.
        ?Publications vivo:relates ?Doc.
        ?Doc a bibo:Document.

        OPTIONAL{?Doc uaslp:crisEstatus1 ?estatus1.}
        OPTIONAL{?Doc uaslp:crisEstatus2 ?estatus2.}

        BIND
        (
            IF(STR(?estatus1)='activo'&& STR(?estatus2)='aceptado',?Doc ,'') AS ?Document
        )

        OPTIONAL{ ?Document vivo:hasPublicationVenue ?Source. }
        OPTIONAL{ ?Document vivo:publisher ?Publisher.}
        OPTIONAL{ ?Document bibo:status ?Status.}
        OPTIONAL{ ?Document scires:documentationFor ?Access.}
        OPTIONAL{ ?Document bibo:presentedAt ?Conference. }
        OPTIONAL{ ?Document vivo:dateTimeValue ?Date. }
        OPTIONAL{ ?Document vivo:hasFundingVehicle ?Funding. }
        OPTIONAL{ ?Document vivo:hasSubjectArea ?SubjectArea. }
        OPTIONAL{ ?Document bibo:cites ?Cites. }
        OPTIONAL{ ?Document bibo:citedBy ?CitedBy. }


    }\"";


    GeneralTransaction($query,$_[1]);

}

# Tablas: editorof, publicaciones
sub UpdateEditorOf
{
    my $query= "\"
    DESCRIBE
    ?Publications
    ?Document
    ?Source
    ?Publisher
    ?Status
    ?Access
    ?Conference
    ?Date
    ?Funding
    ?SubjectArea
    ?Cites
    ?CitedBy
    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador vivo:relatedBy ?Publications.
        ?Publications a vivo:Editorship.

        ?Publications vivo:relates ?Document.
        ?Document a vivo:Document.

        OPTIONAL{ ?Document vivo:hasPublicationVenue ?Source. }
        OPTIONAL{ ?Document vivo:publisher ?Publisher.}
        OPTIONAL{ ?Document bibo:status ?Status.}
        OPTIONAL{ ?Document scires:documentationFor ?Access}
        OPTIONAL{ ?Document bibo:presentedAt ?Conference. }
        OPTIONAL{ ?Document vivo:dateTimeValue ?Date. }
        OPTIONAL{ ?Document vivo:hasFundingVehicle ?Funding. }
        OPTIONAL{ ?Document vivo:hasSubjectArea ?SubjectArea. }
        OPTIONAL{ ?Document bibo:cites ?Cites. }
        OPTIONAL{ ?Document bibo:citedBy ?CitedBy. }
    }
    \"";

    GeneralTransaction($query,$_[1]);

}

# Tablas: eventosxinvestigador, catalogoeventos
sub UpdatePresentations
{
    my $query= "\"DESCRIBE
    ?presenterRole
    ?presenterRoleInterval
    ?presenterRoleStart
    ?presenterRoleEnd
    ?presenterRoleOrg
    ?presenterRoleEvent
    ?includes
    ?occurs

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?presenterRole.

         # presentations
        ?presenterRole a vivo:PresenterRole.
        OPTIONAL{?presenterRole vivo:roleContributesTo ?presenterRoleOrg.}
        OPTIONAL{
            ?presenterRole vivo:dateTimeInterval ?presenterRoleInterval.
            ?presenterRoleInterval vivo:start ?presenterRoleStart.
            ?presenterRoleInterval vivo:end ?presenterRoleEnd.
        }
        ?presenterRole  obo:BFO_0000054 ?presenterRoleEvent.
        OPTIONAL{?presenterRoleEvent  obo:BFO_0000051 ?includes.}
          OPTIONAL{ ?presenterRoleEvent  obo:BFO_0000050 ?occurs.}
    }
    \"";
    GeneralTransaction($query,$_[1]);

}

# Tablas: cainvestigadores, catalogoca
sub UpdatePrincipalInvestigatorOn
{
    my $query= "\"
    DESCRIBE
    ?PrincipalInvRole
    ?PrincipalInvRoleInterval
    ?PrincipalInvRoleEnd
    ?PrincipalInvRoleStart
    ?PrincipalInvOrg

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?PrincipalInvRole.

        ?PrincipalInvRole a vivo:PrincipalInvestigatorRole.
        OPTIONAL{
            ?PrincipalInvRole vivo:dateTimeInterval ?PrincipalInvRoleInterval.
            ?PrincipalInvRoleInterval vivo:start ?PrincipalInvRoleStart.
            ?PrincipalInvRoleInterval vivo:end ?PrincipalInvRoleEnd.
        }
        OPTIONAL{?PrincipalInvRole  vivo:relatedBy ?PrincipalInvOrg.}

    }
    \"";
    GeneralTransaction($query,$_[1]);

}


# Tablas: cainvestigadores, catalogoca
sub UpdateCoPrincipalInvestigatorOn
{
    my $query= "\"DESCRIBE
    ?coPrincipalInvRole
    ?coPrincipalInvRoleInterval
    ?coPrincipalInvRoleEnd
    ?coPrincipalInvRoleStart
    ?coPrincipalInvOrg

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?coPrincipalInvRole.


        ?coPrincipalInvRole a vivo:CoPrincipalInvestigatorRole.
        OPTIONAL{
            ?coPrincipalInvRole vivo:dateTimeInterval ?coPrincipalInvRoleInterval.
            ?coPrincipalInvRoleInterval vivo:start ?coPrincipalInvRoleStart.
            ?coPrincipalInvRoleInterval vivo:end ?coPrincipalInvRoleEnd.
        }
        OPTIONAL{?coPrincipalInvRole  vivo:relatedBy ?coPrincipalInvOrg.}

    }
    \"";
    GeneralTransaction($query,$_[1]);

}

# Tablas: cainvestigadores, catalogoca
sub UpdateInvestigatorOn
{
    my $query= "\"DESCRIBE
    ?InvRole
    ?InvRoleInterval
    ?InvRoleEnd
    ?InvRoleStart
    ?InvOrg

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?InvRole.

        ?InvRole a vivo:InvestigatorRole.
        OPTIONAL{
            ?InvRole vivo:dateTimeInterval ?InvRoleInterval.
            ?InvRoleInterval vivo:start ?InvRoleStart.
            ?InvRoleInterval vivo:end ?InvRoleEnd.
        }
        OPTIONAL{?InvRole  vivo:relatedBy ?InvOrg.}

    }
    \"";
    GeneralTransaction($query,$_[1]);

}

# Tablas: proyectosinvestigadores, proyectosinvestigacion
sub UpdateOtherResearchActivity
{
    my $query= "\"DESCRIBE
    ?ResearcherRole
    ?ResearcherRoleInterval
    ?ResearcherRoleEnd
    ?ResearcherRoleStart
    ?ResearcherOrg

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?ResearcherRole.


        ?ResearcherRole a vivo:ResearcherRole.
        OPTIONAL{
            ?ResearcherRole vivo:dateTimeInterval ?ResearcherRoleInterval.
            ?ResearcherRoleInterval vivo:start ?ResearcherRoleStart.
            ?ResearcherRoleInterval vivo:end ?ResearcherRoleEnd.
        }
        OPTIONAL{?ResearcherRole  vivo:relatedBy ?ResearcherOrg.}

    }\"";
    GeneralTransaction($query,$_[1]);

}


# Tablas: materiasimpartidas, catalogomaterias
sub UpdateTeachingActivities
{
    my $query= "\"DESCRIBE

    ?teacherRole
    ?givenCourse
    ?teacherRoleInterval
    ?teacherRoleStart
    ?teacherRoleEnd

    ?participatesIn
    ?participatesInInterval
    ?participatesInStart
    ?participatesInEnd
    ?Grado
    ?participatesInOrg
    ?academicDegree

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?teacherRole.

        # teaching activities
        ?teacherRole a vivo:TeacherRole.
        OPTIONAL{
            ?teacherRole vivo:dateTimeInterval ?teacherRoleInterval.
            ?teacherRoleInterval vivo:start ?teacherRoleStart.
            ?teacherRoleInterval vivo:end ?teacherRoleEnd.
        }
        OPTIONAL{?teacherRole  obo:BFO_0000054 ?givenCourse.}

        ?Investigador obo:RO_0000056 ?participatesIn.
        OPTIONAL{
            ?participatesIn vivo:dateTimeInterval ?participatesInInterval.
            ?participatesInInterval vivo:start ?participatesInStart.
            ?participatesInInterval vivo:end ?participatesInEnd.
        }

        OPTIONAL{
            ?participatesIn obo:RO_0002234 ?Grado.
            ?Grado a vivo:AwardedDegree.
        }

        OPTIONAL{?participatesIn obo:RO_0000057 ?participatesInOrg.}

        OPTIONAL{
            ?Grado vivo:relates ?academicDegree.
            ?academicDegree a vivo:AcademicDegree.
        }
    }
    \"";
    GeneralTransaction($query,$_[1]);
}

# Tablas: tesisdirigidas, publicaciones, investigadorrevisajournal, colecciones
sub UpdateReviewerOf
{
    my $query= "\"DESCRIBE

    ?reviewerRole
    ?reviewedDocument
    ?reviewerRoleInterval
    ?reviewerRoleStart
    ?reviewerRoleEnd

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?reviewerRole.


        # reviewer of
        ?reviewerRole a vivo:ReviewerRole.
        OPTIONAL{
            ?reviewerRole vivo:dateTimeInterval ?reviewerRoleInterval.
            ?reviewerRoleInterval vivo:start ?reviewerRoleStart.
            ?reviewerRoleInterval vivo:end ?reviewerRoleEnd.
        }
        OPTIONAL{?reviewerRole  vivo:roleContributesTo ?reviewedDocument.}
    }
    \"";
    GeneralTransaction($query,$_[1]);
}



# Tablas: serviceprovider, catalogoeventos, organizaciones, catalogocongresos
sub UpdateProfesionalService
{
    my $query= "\"DESCRIBE
    ?serviceProviderRole
    ?serviceProviderRoleInterval
    ?serviceProviderRoleStart
    ?serviceProviderRoleEnd
    ?serviceProviderRoleOrg
    ?serviceProviderRoleEvent
    ?includes
    ?occurs

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000053 ?serviceProviderRole.

         # presentations
        ?serviceProviderRole a obo:ERO_0000012.

        OPTIONAL{?serviceProviderRole vivo:roleContributesTo ?serviceProviderRoleOrg.}
        OPTIONAL{?serviceProviderRole vivo:dateTimeInterval ?serviceProviderRoleInterval.}
        OPTIONAL{ ?serviceProviderRoleInterval vivo:start ?serviceProviderRoleStart.}
        OPTIONAL{?serviceProviderRoleInterval vivo:end ?serviceProviderRoleEnd.}

        ?serviceProviderRole  obo:BFO_0000054 ?serviceProviderRoleEvent.
        OPTIONAL{?serviceProviderRoleEvent  obo:BFO_0000051 ?includes.}
        OPTIONAL{ ?serviceProviderRoleEvent  obo:BFO_0000050 ?occurs.}
    }
    \"";
    GeneralTransaction($query,$_[1]);

}



# Tablas: formacionacademica, organizaciones
sub UpdateEducationAndTraining
{
    my $query= "\"DESCRIBE

    ?participatesIn
    ?participatesInInterval
    ?participatesInStart
    ?participatesInEnd
    ?Grado
    ?participatesInOrg
    ?academicDegree

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador obo:RO_0000056 ?participatesIn.


        OPTIONAL{
            ?participatesIn vivo:dateTimeInterval ?participatesInInterval.
            ?participatesInInterval vivo:start ?participatesInStart.
            ?participatesInInterval vivo:end ?participatesInEnd.
        }

        OPTIONAL{
            ?participatesIn obo:RO_0002234 ?Grado.
            ?Grado a vivo:AwardedDegree.
        }

        OPTIONAL{?participatesIn obo:RO_0000057 ?participatesInOrg.}

        OPTIONAL{
            ?Grado vivo:relates ?academicDegree.
            ?academicDegree a vivo:AcademicDegree.
        }
    }\"";
    GeneralTransaction($query,$_[1]);

}

# Tablas: premiosinvestigador, organizaciones, catalogopremios
sub UpdateAwardsAndHonors
{

    my $query= "\"DESCRIBE

    ?awardOrHonorReceipt
    ?award
    ?awardYear
    ?awardOrg

    WHERE
    {
        BIND(<$D2R_BASE_URI/individual/$_[0]> AS ?Investigador).
        ?Investigador vivo:relatedBy  ?awardOrHonorReceipt.

        # Awards and honors
        ?awardOrHonorReceipt a vivo:AwardReceipt.
        OPTIONAL{
            ?awardOrHonorReceipt vivo:relates ?award.
            ?award a vivo:Award.
            ?award vivo:assignedBy ?awardOrg.

        }
        OPTIONAL{?awardOrHonorReceipt vivo:dateTimeValue ?awardYear.}

    }\"";
    GeneralTransaction($query,$_[1]);

}

# sub UpdateCuerpoAcademico
# {
#     my $query= '"DESCRIBE

#     ?CuerpoAcademico
#     ?CAInInterval
#     ?CAStart
#     ?CAEnd

#     WHERE
#     {
#         BIND('."<".$D2R_BASE_URI."/individual/".$_[0].">".' AS ?CuerpoAcademico).

#         ?CuerpoAcademico a uaslp:CuerpoAcademico.

#         OPTIONAL{?CuerpoAcademico vivo:dateTimeInterval ?CAInInterval.}
#         OPTIONAL{?CAInInterval vivo:start ?CAStart.}
#         OPTIONAL{?CAInInterval vivo:end ?CAEnd.}



#     }"';
#     GeneralTransaction($query,$_[1]);
# }




#$idInvestigador='7082';

# Hace una consulta SPARQL a D2R para pedir los datos de un investigador
# Parametros:
# * Ruta del "ejecutable" de d2r-query
# * Ruta del archivo de mapeado
# * Id del investigador
# Regresa:
# * Texto en formato .ttl con los datos del investigador y sus relaciones
#
sub d2r_ask_investigador
{

    # Armado de las partes del comando para ejecutar la consulta
    my $D2R_PATH= $_[0];
    my $mapping_file_path=$_[1];
    my $id_investigador= $_[2];
    my $query ='"
    DESCRIBE
    ?Investigador
    # ?vcard
    # ?name
    # ?email
    # ?url
    # ?telephone
    # ?title
    # ?address
    # ?AreaInvestigacion
    # ?geographicFocus
    # ?Positions
    # ?positionOrg

    # ?awardOrHonorReceipt
    # ?award
    # ?awardYear
    # ?awardOrg

    ?presenterRole
    ?presenterRoleInterval
    ?presenterRoleStart
    ?presenterRoleEnd
    ?presenterRoleOrg
    ?presenterRoleEvent
    ?includes
    ?occurs

    # ?attendeeRole
    # ?attendedEvent
    # ?attendeeRoleInterval
    # ?attendeeRoleStart
    # ?attendeeRoleEnd

    # ?organizerRole
    # ?organizedEvent
    # ?organizerRoleInterval
    # ?organizerRoleStart
    # ?organizerRoleEnd

    # ?coPrincipalInvRole
    # ?coPrincipalInvRoleRoleInterval
    # ?coPrincipalInvRoleRoleEnd
    # ?coPrincipalInvRoleRoleStart
    # ?coPrincipalInvOrg

    # ?reviewerRole
    # ?reviewedDocument
    # ?reviewerRoleInterval
    # ?reviewerRoleStart
    # ?reviewerRoleEnd


    # ?teacherRole
    # ?givenCourse
    # ?teacherRoleInterval
    # ?teacherRoleStart
    # ?teacherRoleEnd


    # ?participatesIn
    # ?participatesInInterval
    # ?participatesInStart
    # ?participatesInEnd
    # ?Grado
    # ?participatesInOrg
    # ?academicDegree

    # ?Publications
    WHERE
    {
        ?Investigador a vivo:FacultyMember.
        ?Investigador uaslp:crisid '."'".$id_investigador."'".'^^xsd:integer.

        OPTIONAL{
            ?Investigador obo:ARG_2000028 ?vcard.
            ?vcard vcard:hasName ?name.
            ?vcard vcard:hasEmail ?email.
            ?vcard vcard:hasURL ?url.
            ?vcard vcard:hasTelephone ?telephone.
            ?vcard vcard:hasTitle ?title.
            ?vcard vcard:hasAddress ?address.
            }


        # ?Investigador vivo:hasResearchArea ?AreaInvestigacion.
        # ?Investigador vivo:geographicFocus ?geographicFocus.

        # ?Investigador vivo:relatedBy ?Positions.
        # ?awardOrHonorReceipt,
        # ?Publications.


        # Positions
        # ?Positions a vivo:Position.
        # ?Positions vivo:relates ?positionOrg.

        # Awards and honors
        # ?awardOrHonorReceipt a vivo:AwardReceipt.
        # ?awardOrHonorReceipt vivo:relates ?award.
        # ?awardOrHonorReceipt vivo:dateTimeValue ?awardYear.
        # ?award a vivo:Award.
        # ?award vivo:assignedBy ?awardOrg.

        # selected publications
        # ?Publications a vivo:Authorship.




        ?Investigador obo:RO_0000053 ?presenterRole.
        # ?bearerOf
        # ?coPrincipalInvRole.
        # ?attendeeRole.
        # ?organizerRole.
        # ?teacherRole.
        # ?reviewerRole.
        # ?principalInvRole
        # ?InvestigatorRole.
        # ?researcherRole.

        # # bearer of -- general
        # OPTIONAL{?bearerOf vivo:roleContributesTo ?bearerOfOrg.}
        # OPTIONAL{
        # ?bearerOf vivo:dateTimeInterval ?bearerOfInterval.
        # ?bearerOfInterval vivo:start ?bearerOfStart.
        # ?bearerOfInterval vivo:end ?bearerOfEnd.}
        # OPTIONAL{?bearerOf  obo:BFO_0000054 ?bearerOfEvent.}



        # presentations
        ?presenterRole a vivo:PresenterRole.
        OPTIONAL{?presenterRole vivo:roleContributesTo ?presenterRoleOrg.}
        OPTIONAL{
        ?presenterRole vivo:dateTimeInterval ?presenterRoleInterval.
        ?presenterRoleInterval vivo:start ?presenterRoleStart.
        ?presenterRoleInterval vivo:end ?presenterRoleEnd.}
        OPTIONAL{
            ?presenterRole  obo:BFO_0000054 ?presenterRoleEvent.
            ?presenterRoleEvent  obo:BFO_0000051 ?includes.
            ?presenterRoleEvent  obo:BFO_0000050 ?occurs.
            }




        # co-principal investigator on
        # ?coPrincipalInvRole a vivo:CoPrincipalInvestigatorRole.
        # OPTIONAL{
        #     ?coPrincipalInvRole vivo:dateTimeInterval ?coPrincipalInvRoleRoleInterval.
        #     ?coPrincipalInvRoleRoleInterval vivo:start ?coPrincipalInvRoleStart.
        #     ?coPrincipalInvRoleRoleInterval vivo:end ?coPrincipalInvRoleEnd.
        # }
        # OPTIONAL{?coPrincipalInvRole  vivo:relatedBy ?coPrincipalInvOrg.}


        # attended event
        # ?attendeeRole a vivo:AttendeeRole.
        # OPTIONAL{
        #     ?attendeeRole vivo:dateTimeInterval ?attendeeRoleInterval.
        #     ?attendeeRoleInterval vivo:start ?attendeeRoleStart.
        #     ?attendeeRoleInterval vivo:end ?attendeeRoleEnd.
        # }
        # OPTIONAL{?attendeeRole  obo:BFO_0000054 ?attendedEvent.}


        # organizer of event
        # ?organizerRole a vivo:OrganizerRole.
        # OPTIONAL{
        # ?organizerRole vivo:dateTimeInterval ?organizerRoleInterval.
        # ?organizerRoleInterval vivo:start ?organizerRoleStart.
        # ?organizerRoleInterval vivo:end ?organizerRoleEnd.}
        # OPTIONAL{?organizerRole obo:BFO_0000054 ?organizedEvent.}


        # reviewer of
        # ?reviewerRole a vivo:ReviewerRole.
        # ?reviewerRole vivo:dateTimeInterval ?reviewerRoleInterval.
        # ?reviewerRoleInterval vivo:start ?reviewerRoleStart.
        # ?reviewerRoleInterval vivo:end ?reviewerRoleEnd.
        # ?reviewerRole  vivo:roleContributesTo ?reviewedDocument.


        # teaching activities
        # ?teacherRole a vivo:TeacherRole.
        # ?teacherRole vivo:dateTimeInterval ?teacherRoleInterval.
        # ?teacherRoleInterval vivo:start ?teacherRoleStart.
        # ?teacherRoleInterval vivo:end ?teacherRoleEnd.
        # ?teacherRole  obo:BFO_0000054 ?givenCourse.

        # EDUCATION AND TRAINING
        # ?Investigador obo:RO_0000056 ?participatesIn.
        # ?participatesIn vivo:dateTimeInterval ?participatesInInterval.
        # ?participatesInInterval vivo:start ?participatesInStart.
        # ?participatesInInterval vivo:end ?participatesInEnd.

        # ?participatesIn obo:RO_0002234 ?Grado.
        # ?Grado a vivo:AwardedDegree.

        # ?participatesIn obo:RO_0000057 ?participatesInOrg.
        # ?Grado vivo:relates ?academicDegree.
        # ?academicDegree a vivo:AcademicDegree.


    }"';
    #print $cgi->header('text/json');
    # print $query;
    # Se ejecuta el comando con la consulta
    my $result = `$D2R_PATH -f ttl  $mapping_file_path $query`;

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


    if($ttl_data eq "")
    {
        $ttl_data="Error: Investigador no encontrado";
    }

    return $ttl_data;


}



# Hace una consulta SPARQL a D2R.
# Parametros:
# * texto de la consulta
# Regresa:
# * Texto en formato .ttl con los datos requeridos por la consulta
#
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

# Realiza eliminación e insercion de datos en VIVO usando la API SPARQL update
# Parametros:
# 1 Texto en formato .ttl con la informacion a insertar o eliminar.
# 2 'insert' o 'delete' para especificar la accion a realizar, no iumportan mayusculas o minusculas.
# Regresa:
# 1 si la modificacione es correcta, 0 si ocurrió algun error.
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








print $cgi->header('text/json');

# UpdateVcard($idInvestigador,'insert');
# UpdatePositions($idInvestigador,'insert');
# UpdateResearchAreas($idInvestigador,'insert');
# UpdateGeographicFocus($idInvestigador,'insert');
# UpdateHeadOf($idInvestigador,'insert');
# UpdateMemberOf($idInvestigador, 'insert');
# UpdateAttendedAndOrganizedEvent($idInvestigador, 'insert');
# UpdatePublications($idInvestigador,'insert');
# UpdateEditorOf($idInvestigador, 'insert');
# UpdatePresentations($idInvestigador,'insert');
# UpdatePropiedades($idInvestigador, 'insert');
# UpdatePrincipalInvestigatorOn($idInvestigador,'insert');
# UpdateCoPrincipalInvestigatorOn($idInvestigador,'insert');
# UpdateInvestigatorOn($idInvestigador,'insert');
# UpdateOtherResearchActivity($idInvestigador,'insert');
# UpdateTeachingActivities($idInvestigador,'insert');
# UpdateReviewerOf($idInvestigador,'insert');
# UpdateEducationAndTraining($idInvestigador,'insert');
# UpdateAwardsAndHonors($idInvestigador,'insert');
# UpdateProfesionalService($idInvestigador,'insert');
# UpdateCuerpoAcademico($idInvestigador, 'insert');

# UpdatePublicacion($idInvestigador,'insert');