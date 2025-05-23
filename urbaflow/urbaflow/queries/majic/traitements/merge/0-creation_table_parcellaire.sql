DROP TABLE IF EXISTS parcellaire;

CREATE TABLE parcellaire AS (
    SELECT
        cadastre_parcelles.geo_parcelle AS idparcelle_geom,
        cadastre_parcelles.commune AS code_insee,
        parcelle.ccodir,
        parcelle.ccopre,
        parcelle.dnupla,
        parcelle.dnupro,
        parcelle.comptecommunal,
        parcelle.dcntpa,
        parcelle.gpdl,
        parcelle.dnupdl,
        parcelle.cprsecr,
        parcelle.ccosecr,
        parcelle.dnuplar,
        parcelle.dparpi,
        parcelle.gparnf,
        parcelle.gparbat,
        parcelle.dnvoiri,

        parcelle.dindic,
        parcelle.ccoriv,
        parcelle.cconvo,
        null::text AS dlibvoi,
        null::text AS libcom,
        null::text AS adressepar,
        null::numeric AS ndroit,
        null::numeric AS ndroitindi,
        null::text AS typedroit,
        null::text AS descprop,
        null::numeric AS ndroitpro,
        null::numeric AS ndroitges,
        null::numeric AS ndroitpro_parcelle_bati,
        null::text AS catpro,
        null::text AS catpro_niv2,
        null::text AS presgdprop,
        null::text AS typprop,
        null::text AS typproppro,
        null::text AS typpropges,
        null::text AS catproppro,
        null::text AS catpropges,
        null::text AS ddenomprop,
        null::text AS ddenomproppro,
        null::text AS ddenompropges,
        null::numeric AS nlot,
        null::text AS pdlmp,
        parcelle.jdatat,
        null::text AS jdatatv,
        null::integer AS jdatatan,
        null::integer AS jannatmin,
        null::integer AS jannatmax,
        null::integer AS jannatminh,
        null::integer AS jannatmaxh,
        null::integer AS janbilmin,
        null::integer AS dcntarti,
        null::integer AS dcntnaf,
        null::numeric AS dcnt10,
        null::numeric AS nbat,
        null::numeric AS nlocal,
        null::numeric AS nlocmaison,
        null::numeric AS nlocappt,
        null::numeric AS nlocdep,
        null::numeric AS nloccom,
        null::numeric AS nloclog,
        null::numeric AS nloccomsec,
        null::numeric AS nloccomter,
        null::numeric AS nlocburx,
        null::text AS tlocdomin,
        null::numeric AS stoth,
        null::numeric AS smoyh,
        null::numeric AS npiecemoy,
        null::numeric AS stotdsueic,
        null::numeric AS nlogh,
        null::numeric AS nloghvac,
        null::numeric AS nloghmeu,
        null::numeric AS nloghloue,
        null::numeric AS nloghpp,
        null::numeric AS nloghautre,
        null::numeric AS nloghnonh,
        null::numeric AS nhabvacant,
        null::numeric AS nactvacant,
        null::numeric AS noccprop,
        null::numeric AS nocclocat,
        null::text AS typoocc,
        null::numeric AS nmediocre,
        null::numeric AS nloghlm,
        null::numeric AS npevp,
        null::numeric AS stotp,
        null::numeric AS smoyp,
        null::numeric AS npevd,
        null::numeric AS stotd,
        null::numeric AS smoyd,
        null::numeric AS spevtot,
        null::text AS tpevdom_n,
        null::text AS tpevdom_s,
        null::smallint AS ncp,
        st_transform(
            st_setsrid(cadastre_parcelles.wkb_geometry, 4326), 2154
        ) AS geom,
        left(cadastre_parcelles.commune, 2) AS ccodep,
        right(cadastre_parcelles.commune, 3) AS ccocom,
        trim(cadastre_parcelles.section) AS ccosec,
        cadastre_parcelles.commune
        || cadastre_parcelles.prefixe
        || cadastre_parcelles.section
        || left(
            '0000', 4 - length(cadastre_parcelles.numero)
        ) || cadastre_parcelles.numero AS idpar,
        cadastre_parcelles.commune
        || cadastre_parcelles.prefixe
        || cadastre_parcelles.section AS idsec,
        parcelle.ccodep || parcelle.ccocom || parcelle.dnupro AS idprocpte,
        parcelle.ccodep
        || parcelle.ccocom
        || parcelle.cprsecr
        || parcelle.ccosecr
        || parcelle.dnuplar AS idparref,
        parcelle.ccodep
        || parcelle.ccocom
        || parcelle.cprsecr
        || parcelle.ccosecr AS idsecref,
        parcelle.ccodep || parcelle.ccocom || parcelle.ccoriv AS idvoie,
        trim(parcelle.ccodep || parcelle.ccocom) AS idcom,
        cadastre_parcelles.section || left(
            '0000', 4 - length(cadastre_parcelles.numero)
        ) || cadastre_parcelles.numero AS idpar_simple

    FROM cadastre_parcelles
    LEFT JOIN parcelle
        ON (cadastre_parcelles.geo_parcelle = parcelle.parcelle)
);

--DROP TABLE temp_parcellaire;
-- index
CREATE INDEX parcelle_idprocpte_idx ON parcellaire
USING btree (idprocpte);

CREATE INDEX parcelle_idpar_idx ON parcellaire
USING btree (idpar);
