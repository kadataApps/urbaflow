# Objectifs du projet

- Adapter les scripts pour construire:
  - une table parcelle avec le maximum d'informations sur la structure foncière et sur le bâti
  - une table propriétaire avec le maximum d'informations sur les propriétaires

L'exploitation de cette base permettra d'alimenter les "fiches sites".


## Données à récupérer

### table parcelle

Liste des champs des Fichiers Fonciers à récupérer:

voir http://doc-datafoncier.cerema.fr/ff/doc_fftp/table/pnb10_parcelle/last/

* : les champs qui ne sont pas utiles dans la table finale
** : les champs qui pourraient être utiles mais peu utilisés
--: champ non utile si correctement remplacé par le champ adresse
+ : champ "prioritaire"

idpar
*idsec
idprocpte
*idparref
*idsecref
*idvoie
idcom
idcomtxt
ccodep
ccodir
*ccocom
ccopre
ccosec
dnupla
dcntpa
dnupro
jdatat
jdatatv
*dreflf
gpdl
*cprsecr
*ccosecr
**dnuplar
*dnupdl
**gurbpa
*dparpi
*ccoarp
*gparnf
**gparbat
--dnuvoi
--dindic
--ccovoi
--ccoriv
--ccocif
--cconvo
--dvoilib
**idparm
**ccocomm
**ccoprem
**ccosecm
**dnuplam
**type
**typetxt
*ccoifp
jdatatan
jannatmin
jannatmax
jannatminh
jannatmaxh
*janbilmin
*nsuf
*ssuf
*cgrnumd
cgrnumdtxt
dcntsfd
dcntarti
dcntnaf
**dcnt01
**dcnt02
**dcnt03
**dcnt04
**dcnt05
**dcnt06
**dcnt07
**dcnt08
**dcnt09
**dcnt10
**dcnt11
**dcnt12
**dcnt13
*schemrem
nlocal
nlocmaison
nlocappt
nloclog
nloccom
nloccomrdc
nloccomter
**ncomtersd
**ncomterdep
nloccomsec
nlocdep
nlocburx
**tlocdomin
nbat
nlochab
nlogh
nloghmais
nloghappt
npevph
stoth
stotdsueic
nloghvac
loghmeu
nloghloue
nloghpp
nloghautre
nloghnonh
nactvacant
nloghvac2a
nactvac2a
nloghvac5a
nactvac5a
*nmediocre
nloghlm
nloghlls
*npevd
*stotd
*npevp
*sprincp
*ssecp
*ssecncp
**sparkp
**sparkncp
*slocal
*tpevdom_s
nlot
pdlmp
ctpdl
typecopro2
+ncp
ndroit
+ndroitindi
+ndroitpro
*ndroitges
*catpro2
*catpro2txt
**catpro3
+catpropro2
*catproges2
**locprop
**locproptxxt
*geomloc
geompar
**source_geo
*vecteur
*contour
*idpk


Champ à ajouter:
addresse: libellé de l'adresse de la parcelle

### table propriétaires

idprodroit
idprocpte
idpersonne
*idvoie
idcom
idcomtxt
ccodep
*ccodir
*ccocom
dnupro
dnulp
*ccocif
dnuper
ccodro
+ccodrotxt
+typedroit
**ccodem
**ccodemtxt
*gdesip
*gtoper
*ccoqua
*dnatpr
*dnatprtxt
*ccogrm
*ccogrmtxt
**dsglpm
**dforme
ddenom
*gtyp3
*gtyp4
*gtyp5
*gtyp6
*dlign3
*dlign4
*dlign5
*dlign6
**ccopay
*ccddep1a2
*ccodira
*ccocomadr
*ccovoi
*ccoriv
*dnvoiri
*dindic
*ccopos
*dqualp
*dnomlp
*dprnlp
+jdatnss
*dldnss
+dsiren
*topja
*datja
*dformjur
*dnomus
*dprnus
*locprop
*locproptxt
*catpro2
catpro2txt
*catpro3
**catpro3txt
*idpk


## Documentation

