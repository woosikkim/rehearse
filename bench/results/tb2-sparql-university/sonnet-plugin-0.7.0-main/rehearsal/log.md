$ cd /app; ls -a; wc -l university_graph.ttl; head -60 university_graph.ttl; which arq sparql python3; python3 -c 'import rdflib;print(rdflib.__version__)'
Exit code 1
.
..
.rehearsal
university_graph.ttl
305 university_graph.ttl
@prefix uni: <http://university.org/ontology/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
# ---------------------------
# Universities
# ---------------------------
uni:ETHZurich a uni:University ;
    uni:hasName "ETH Zurich" ;
    uni:locatedInCountry "CH" .
uni:UPM a uni:University ;
    uni:hasName "Universidad Politécnica de Madrid" ;
    uni:locatedInCountry "ES" .
uni:IST a uni:University ;
    uni:hasName "Instituto Superior Técnico" ;
    uni:locatedInCountry "PT" .
uni:NTUA a uni:University ;
    uni:hasName "National Technical University of Athens" ;
    uni:locatedInCountry "GR" .
uni:NKUA a uni:University ;
    uni:hasName "National and Kapodistrian University of Athens" ;
    uni:locatedInCountry "GR" .
uni:Sorbonne a uni:University ;
    uni:hasName "Sorbonne University" ;
    uni:locatedInCountry "FR" .
uni:MIT a uni:University ;
    uni:hasName "Massachusetts Institute of Technology" ;
    uni:locatedInCountry "US" .
uni:Berkeley a uni:University ;
    uni:hasName "University of California, Berkeley" ;
    uni:locatedInCountry "US" .
uni:LMU a uni:University ;
    uni:hasName "Ludwig Maximilian University of Munich" ;
    uni:locatedInCountry "DE" .
# ---------------------------
# Departments

$ cd /app; sed -n 60,305p university_graph.ttl; pip install rdflib 2>&1 | tail -1
uni:Biology_MIT a uni:Department ;
    uni:belongsTo uni:MIT .
uni:Sloan_MIT a uni:Department ;
    uni:belongsTo uni:MIT .
uni:Engineering_LMU a uni:Department ;
    uni:belongsTo uni:LMU .
uni:Engineering_Berkeley a uni:Department ;
    uni:belongsTo uni:Berkeley .
uni:Robotics_UPM a uni:Department ;
    uni:belongsTo uni:UPM .
uni:HistoryAndPhilosophy_NKUA a uni:Department ;
    uni:belongsTo uni:NKUA .
# ---------------------------
# Courses
# ---------------------------
uni:CS101 a uni:Course ;
    uni:isTaughtIn uni:ComputerScience_NTUA .
uni:AI101 a uni:Course ;
    uni:isTaughtIn uni:ComputerScience_NTUA .
uni:Math101 a uni:Course ;
    uni:isTaughtIn uni:Mathematics_IST .
uni:Math201 a uni:Course ;
    uni:isTaughtIn uni:Mathematics_Sorbonne .
uni:Physics301 a uni:Course ;
    uni:isTaughtIn uni:Physics_ETH .
uni:Bio101 a uni:Course ;
    uni:isTaughtIn uni:Biology_MIT .
uni:Eng202 a uni:Course ;
    uni:isTaughtIn uni:Engineering_LMU .
uni:EngUS302 a uni:Course ;
    uni:isTaughtIn uni:Engineering_Berkeley .
uni:STS101 a uni:Course ;
    uni:isTaughtIn uni:HistoryAndPhilosophy_NKUA .
# ---------------------------
# Professors 
# ---------------------------
uni:Orfeas_Menis a uni:Person ;
    uni:hasName "Orfeas Menis" ;
    uni:role "Professor of Computer Science" ;
    uni:teaches uni:CS101 ;

$ cd /app; cat > solution.sparql <<'EOF'
PREFIX uni: <http://university.org/ontology/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?professorName (GROUP_CONCAT(DISTINCT ?country; separator=", ") AS ?countries)
WHERE {
  ?prof uni:hasName ?professorName ;
        uni:role ?role ;
        uni:worksIn ?dept .
  FILTER(REGEX(?role, "^Professor\\b"))
  ?dept uni:belongsTo ?univ .
  ?univ uni:locatedInCountry ?country .
  # at least one of the professor's departments is in an EU university
  FILTER EXISTS {
    ?prof uni:worksIn ?euDept .
    ?euDept uni:belongsTo/uni:locatedInCountry ?euCountry .
    FILTER(?euCountry IN ("AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"))
  }
  # at least one of the professor's departments has more than 10 current students
  FILTER EXISTS {
    ?prof uni:worksIn ?busyDept .
    {
      SELECT ?busyDept (COUNT(DISTINCT ?student) AS ?n)
      WHERE {
        ?course uni:isTaughtIn ?busyDept .
        ?student uni:isEnrolledIn ?course ;
                 uni:hasEnrollmentDate ?enrolled .
        OPTIONAL { ?student uni:hasGraduationDate ?graduated }
        FILTER(?enrolled <= "2025-08-16"^^xsd:date)
        FILTER(!BOUND(?graduated) || ?graduated > "2025-08-16"^^xsd:date)
      }
      GROUP BY ?busyDept
      HAVING (COUNT(DISTINCT ?student) > 10)
    }
  }
}
GROUP BY ?professorName
EOF
python3 -m pip install rdflib 2>&1 | tail -1; ls ~/.m2 /usr/share/java 2>/dev/null | head
/usr/bin/python3: No module named pip

