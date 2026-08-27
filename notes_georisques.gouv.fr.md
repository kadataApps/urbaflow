# Notes sur Georisques.gouv.fr

Objectif: Trouver les urls des services web de Géorisques permettant de télécharger les données de risques pour un département donné (données au format csv ou fiches de chaque site)

Contenu de https://www.georisques.gouv.fr//themes/custom/georisques/assets/dist/js/georisques_commun/web-service-urls.json :

```json
{
    "BASE": "https://www.georisques.gouv.fr/webappReport/ws",
    "INST": "https://www.georisques.gouv.fr/webappReport/ws/installations",
    "IREP": "https://www.georisques.gouv.fr/webappReport/ws/irep",
    "INFOSOLS": "https://www.georisques.gouv.fr/webappReport/ws/infosols",
    "BASIAS": "https://www.georisques.gouv.fr/webappReport/ws/basias",
    "GASPAR": "https://www.georisques.gouv.fr/webappReport/ws/gasparv2",
    "DOWNLOAD": "https://www.georisques.gouv.fr/webappReport/ws/telechargement",
    "BASETELECHARGEMENT": "https://www.georisques.gouv.fr/webappReport/ws/telechargements",
    "INSEE": "https://www.georisques.gouv.fr/webappReport/ws/insee",
    "GEO": "https://geo.api.gouv.fr",
    "PDF":"https://www.georisques.gouv.fr/pdfReport/pdf"
}
```

Contenu de https://www.georisques.gouv.fr/themes/custom/georisques/assets/dist/js/georisques_commun/infosols-properties.json

```json
{
    "adresseFicheInfosols": "http://fiches-risques.brgm.fr/georisques/infosols/",
    "adresseFicheCasias": "http://fiches-risques.brgm.fr/georisques/casias/",
    "aucunResultat": "Aucun résultat trouvé pour cette recherche",
    "erreurCategorisation": "Le choix d’une catégorisation est obligatoire",
    "erreurSousCategorie": "Le choix d’une sous-catégorie est obligatoire",
    "erreurFormatIdentifiant": "Le format de l'identifiant est incorrect"
  }
```

  Code source du script de téléchargement:
  
  ```javascript
  (function ($) {
    var wsUrlInstSSP = function() {
        var properties = {};

        $.ajaxSetup({
            async: false
        });

        $.getJSON("/themes/custom/georisques/assets/dist/js/georisques_commun/web-service-urls.json", function (data) {
            properties = data;
        });

        $.ajaxSetup({
            async: true
        });

        return properties.INST;
    }

    var wsUrlInfosolsSSP = function() {
        var properties = {};

        $.ajaxSetup({
            async: false
        });

        $.getJSON("/themes/custom/georisques/assets/dist/js/georisques_commun/web-service-urls.json", function (data) {
            properties = data;
        });

        $.ajaxSetup({
            async: true
        });

        return properties.INFOSOLS;
    }

    var app = $.sammy(function () {
        this.use('Hogan', 'hg');

        var str = window.location.href;
        var pageSize = 10;
        var nombreDePage;
        var start = this.start || 0;

        getJSONProperties = function() {
            var properties = {};

            $.ajaxSetup({
                async: false
            });

            $.getJSON("/themes/custom/georisques/assets/dist/js/georisques_commun/infosols-properties.json", function (data) {
                properties = data;
            });

            $.ajaxSetup({
                async: true
            });

            return properties;
        }


        function getParamUrl() {
            var url = location.hash.split('#/')[1];
            var paramUrl = {};

            if (url !== '') {
                url = url.split('&');

                for (var index in url) {
                    var param = url[index];
                    paramUrl[param.split('=')[0]] = param.split('=')[1];
                }
            }

            return paramUrl;
        };


        function getPageLink(num) {
            var pageLink = '#/';
            var paramUrl = getParamUrl();

            paramUrl['page'] = num;

            if (paramUrl['type']) {
                pageLink = pageLink + "type=" + paramUrl['type'];
            }

            if (paramUrl['region']) {
                if (pageLink !== '#/') {
                    pageLink = pageLink + "&region=" + paramUrl['region'];
                } else {
                    pageLink = pageLink + "region=" + paramUrl['region'];
                }
            }

            if (paramUrl['departement']) {
                if (pageLink !== '#/') {
                    pageLink = pageLink + "&departement=" + paramUrl['departement'];
                } else {
                    pageLink = pageLink + "departement=" + paramUrl['departement'];
                }
            }

            if (paramUrl['commune']) {
                if (pageLink !== '#/') {
                    pageLink = pageLink + "&commune=" + paramUrl['commune'];
                } else {
                    pageLink = pageLink + "commune=" + paramUrl['commune'];
                }
            }


            if (pageLink !== '#/') {
                pageLink = pageLink + "&page=" + num;
            } else {
                pageLink = pageLink + "page=" + num;
            }

            if (paramUrl['type'] == 'classification') {
                pageLink = pageLink + "&statut=" +   paramUrl['statut'].toUpperCase();
            }

            return pageLink;
        };


        function getType() {
            var type = "instruction";

            if ($('#isInstruction').val() === "false") {
                type = "classification";
            }

            return type;
        };


        function isInstruction() {
            var isInstruction = true;

            if ($('#isInstruction').val() === "false") {
                isInstruction = false;
            }

            return isInstruction;
        };


        function callbackLoad(ctx, data, page) {
            var instructionBool = isInstruction();
            var type = getType();
            var paramUrl = getParamUrl();
            var jsonProperties = getJSONProperties();
            var countTotal = data["x-total-count"][0].value;
            var urlCarte = '';
            var urlDownload = '';

            if (paramUrl['commune']) {
                urlCarte = location.pathname + "/carte#/admin/com/" + paramUrl['commune'];
            } else if (paramUrl['departement']) {
                urlCarte = location.pathname + "/carte#/admin/dpt/" + paramUrl['departement'];
            } else if (paramUrl['region']) {
                urlCarte = location.pathname + "/carte#/admin/reg/" + paramUrl['region'];
            } else {
                urlCarte = location.pathname + "/carte#/admin/fxx";
            }

            urlDownload = wsUrlInfosolsSSP() + '/basol/_search?'
                + 'isExport=true'
                + (paramUrl['region'] ? '&codeRegion=' + paramUrl['region'] : '')
                + (paramUrl['departement'] ? '&codeDepartement=' + paramUrl['departement'] : '')
                + (paramUrl['commune'] ? '&codeCommune=' + paramUrl['commune'] : '')
                + (paramUrl['cdGroupe'] ? '&codeGroupeSubstance=' + paramUrl['cdGroupe'] : '')
                + (paramUrl['nom'] ? '&nomEtablissement=' + decodeURI(paramUrl['nom']) : '');


            var param = {
                urlFiche: jsonProperties.adresseFicheInfosols,
                booleanInstruction: instructionBool,
                type: type,
                region: paramUrl['region'],
                departement: paramUrl['departement'],
                commune: paramUrl['commune'],
                count: pageSize,
                countTotal: countTotal,
                hasData: countTotal === '0' ? false : true,
                numberPage: 0,
                list: data.data,
                number: '{{number}}',
                minIdx: ((page * pageSize) - pageSize) + 1,
                maxIdx: (page * pageSize),
                pages: paginate(start, countTotal),
                urlCarte: urlCarte,
                urlDownload: urlDownload
            };

            sizeCount = param.countTotal;

            if (param.countTotal < pageSize) {
                param.maxIdx = param.countTotal;
                param.count = param.countTotal;
                param.numberPage = 1;
            } else {
                if (param.countTotal % pageSize !== 0) {
                    param.numberPage = Math.ceil(param.countTotal / pageSize);
                } else {
                    param.numberPage = (param.countTotal / pageSize);
                }
            }

            if (param.countTotal < param.maxIdx) {
                param.maxIdx = param.countTotal;
            }

            var template = '#tpl-infosols';

            if (countTotal === '0' || !countTotal) {
                template = '#tpl-infosolsEmpty-infosolsEmpty';
                param.aucunResultat = jsonProperties['aucunResultat'];
            }

            nombreDePage = param.numberPage;

            if (ctx.hg === undefined) {
                var cached_templates = {};

                ctx.hg = function (template, data, partials) {
                    var compiled_template = cached_templates[compiled_template];

                    if (!compiled_template) {
                        compiled_template = Hogan.compile(template);
                    }

                    data = $.extend({}, this, data);
                    partials = $.extend({}, data.partials, partials);

                    return compiled_template.render(data, partials);
                };

            }

            $('#sammyListeResultatInfosols').html(ctx.hg($(template).html(), param));

            $('#page-selection').hide();

            $('#page-selection').bootpag({
                total: nombreDePage,
                maxVisible: 8,
                leaps: false,
                firstLastUse: true,
                first: '<i style="padding-top:0.6rem" class="light round-small fas fa-angle-double-left"></i>',
                last: '<i style="padding-top:0.6rem" class=" light round-small fas fa-angle-double-right"></i>',
                prev: '<i style="padding-top:0.6rem" class=" light round-small fas fa-angle-left"></i>',
                next: '<i style="padding-top:0.6rem" class="light round-small fas fa-angle-right"></i>',
                page: (paramUrl.page ? paramUrl.page : 1)
            }).on("page", function (event, num) {
                document.location.href = getPageLink(num);
            });

            if(nombreDePage > 1) {
                $('#page-selection').show();
            }

            $("li.first.disabled a").html('<i style="padding-top:0.6rem" class="round-small-white  fas fa-angle-double-left"></i>');
            $("li.prev.disabled a").html('<i style="padding-top:0.6rem" class="round-small-white  fas fa-angle-left"></i>');
            $("li.last.disabled a").html('<i style="padding-top:0.6rem" class="round-small-white  fas fa-angle-double-right"></i>');
            $("li.next.disabled a").html('<i style="padding-top:0.6rem" class="round-small-white  fas fa-angle-right"></i>');
        };


        function loadSites(ctx, page) {
            if (!page) {
                page = 1;
            }

            var type = getType();
            var paramUrl = getParamUrl();
            var searchParamsUrl = 'type=' + type + '&page=' + (page - 1) + '&size=' + pageSize;

            var statutClassification
            if (paramUrl['statut']) {
                statutClassification = '&statut=' + paramUrl['statut'].toUpperCase();
            }
            else {
                statutClassification = '';
            }

            var nomEtablissement;
            if (paramUrl['nom']) {
                nomEtablissement = '&nomEtablissement=' + decodeURI(paramUrl['nom']);
            }
            else {
                nomEtablissement = '';
            }

            if (paramUrl['region']) {
                var localisationRegion = '&codeRegion=' + paramUrl['region'];
            } else {
                var localisationRegion = '';
            }

            if (paramUrl['departement']) {
                var localisationDepartement = '&codeDepartement=' + paramUrl['departement'];
            } else {
                var localisationDepartement = '';
            }

            if (paramUrl['commune']) {
                var localisationCommune = '&codeCommune=' + paramUrl['commune'];
            } else {
                var localisationCommune = '';
            }

            var codeGroupeSubstance;
            if ('XXX' === paramUrl['cdSubs'] && paramUrl['cdGroupe']) {
                codeGroupeSubstance = '&codeGroupeSubstance=' + paramUrl['cdGroupe'];
            }
            else {
                codeGroupeSubstance = '';
            }

            var codeSubstance;
            if ('XXX' !== paramUrl['cdSubs'] && paramUrl['cdGroupe']) {
                codeSubstance = '&codeSubstance=' + paramUrl['cdSubs'];
            }
            else {
                codeSubstance = '';
            }

            searchParamsUrl = searchParamsUrl + statutClassification + nomEtablissement +
                localisationRegion + localisationDepartement + localisationCommune +
                codeGroupeSubstance + codeSubstance;

            var prefix = wsUrlInfosolsSSP();
            var urlLoad = prefix + '/resultats/recherche?' + searchParamsUrl;

            $.getJSON(urlLoad).done(function (data) {
                callbackLoad(ctx, data, page)
            })
        };

        function paginate(page, count) {
            var nbPages = Math.ceil(count / pageSize);
            var pages = [];

            if (nbPages > 1) {
                for (i = 0; i < nbPages; i++) {
                    pages.push({
                        "number": i + 1,
                        "class": i + 1 === page ? "current" : ""
                    });
                }
            }

            return pages;
        };


        this.get('#/', function () {
            this.redirect('#/data');
        });

        this.get('#/data', function () {
            var paramUrl = getParamUrl();

            if (paramUrl['type'] === 'classification') {
                $('#isInstruction').val('false');
                $('#classification').addClass("button-detail-on");
                $('#classification').removeClass("button-detail-off");
                $("#instruction").addClass("button-detail-off");
                $("#instruction").removeClass("button-detail-on");
                $('#classificationStatut').show();
                $('#polluantWrapper').hide();

                if (paramUrl['statut'] === 'sis') {
                    $('#classificationSis').addClass("button-detail-on");
                    $('#classificationSis').removeClass("button-detail-off");
                    $("#classificationSup").addClass("button-detail-off");
                    $("#classificationSup").removeClass("button-detail-on");
                }
                else if (paramUrl['statut'] === 'sup') {
                    $('#classificationSup').addClass("button-detail-on");
                    $('#classificationSup').removeClass("button-detail-off");
                    $("#classificationSis").addClass("button-detail-off");
                    $("#classificationSis").removeClass("button-detail-on");
                }
                else {
                    $("#classificationSis").addClass("button-detail-off");
                    $("#classificationSis").removeClass("button-detail-on");
                    $("#classificationSup").addClass("button-detail-off");
                    $("#classificationSup").removeClass("button-detail-on");
                }
            } else if (paramUrl['type'] === 'instruction') {
                $('#isInstruction').val('true');
                $('#instruction').addClass("button-detail-on");
                $('#instruction').removeClass("button-detail-off");
                $("#classification").addClass("button-detail-off");
                $("#classification").removeClass("button-detail-on");
                $('#classificationStatut').hide();
                $('#polluantWrapper').show();
            } else {
                $('#instruction').addClass("button-detail-off");
                $('#instruction').removeClass("button-detail-on");
                $("#classification").addClass("button-detail-off");
                $("#classification").removeClass("button-detail-on");
            }

            if (paramUrl['nom']) {
                var nom = decodeURI(paramUrl['nom']);
                $('#nomSite').val(nom);
            }

            var launchQuery = false;
            if (paramUrl['region']) {
                $("#departement").prop("disabled", false);
                $("#departement").removeClass("form-disabled");

                if (paramUrl['departement']) {
                    $("#commune").prop("disabled", false);
                    $("#commune").removeClass("form-disabled");
                }
                else {
                    $("#commune").prop("disabled", true);
                    $("#commune").addClass("form-disabled");
                }
            }
            else {
                $("#departement").prop("disabled", true);
                $("#departement").addClass("form-disabled");
                $("#commune").prop("disabled", true);
                $("#commune").addClass("form-disabled");

                launchQuery = paramUrl['departement'] && paramUrl['commune'];
            }

            //on verifie que la div existe pour charger les données
            if ($('#nomTerritoire').length) {
                app.initRegSelect(paramUrl['region']);
                app.initDptSelect(paramUrl['region'], paramUrl['departement']);
                app.initComSelect(paramUrl['departement'], paramUrl['commune']);
                app.initPolluantsTree(paramUrl['cdGroupe'],paramUrl['cdSubs']);
                setTimeout(() => {
                    $('#region').niceSelect('update');
                    $('#departement').niceSelect('update');
                    $('#commune').niceSelect('update');
                }, 1000);
            }

            if (launchQuery) {
                app.reloadSites(this);
            }

            if (paramUrl['page'] && $('#firstSearch').val() === 'false') {
                loadSites(this, paramUrl['page']);
            }

            $('#firstSearch').val('false');
        });

        $.extend(Sammy.Application.prototype, {
            regions: null,
            departements: {},
            communes: {},
            polluants: null,
            wsUrl: wsUrlInstSSP(),
            pageSize: 10,

            initPolluantsTree(cdGroupe, cdSubs) {

                if (!this.polluants) {
                    $.getJSON(
                        wsUrlInfosolsSSP() + '/instructions/polluant',
                        function(res) {
                            this.polluants = res;

                            $('#treePolluants').html('');
                            $('#treePolluants').treeview(app.buildTree(res));
                        });
                }
                else {
                    $('#treePolluants').html('');
                    $('#treePolluants').treeview(app.buildTree(res, cdGroupe, cdSubs));
                }
            },

            buildTree(data, cdGroupe, cdSubs) {
                return {
                    data: app.builTreeNodes(data, cdGroupe, cdSubs),
                    multiSelect: false,
                    selectedBackColor: '#E95182',

                    onNodeSelected: function (e, d) {
                        $("#listePolluants option").remove();

                        var optionToAdd = $('<option>')
                            .val(d.codeGroupe + '::' + d.codeSubstance)
                            .text(d.text);

                        $('#ModPolluant').modal('hide');
                        $('#listePolluants').append(optionToAdd);
                        $('#listePolluants').change();
                    },

                    onNodeUnselected: function (e, d) {
                        $("#listePolluants option").remove();
                        $('#listePolluants').change();
                    }
                };
            },

            builTreeNodes(data, cdGroupe, cdSubs) {
                var nodes = [];

                for (groupe of data) {
                    var subNodes = groupe.substances.map(elm => {
                        return {
                            text: elm.substance,
                            codeGroupe: groupe.codeGroupeSubstance,
                            codeSubstance: elm.codeSubstance,
                            selectable: true,
                            state: {
                                expanded: false,
                                selected: cdGroupe && cdGroupe === groupe.codeGroupeSubstance && cdSubs && cdSubs === elm.codeSubstance
                            },
                            nodes: []
                        }
                    });

                    var node = {
                        text: groupe.groupeSubstance,
                        codeGroupe: groupe.codeGroupeSubstance,
                        codeSubstance: 'XXX',
                        selectable: true,
                        state: {
                            expanded: false,
                            selected: cdGroupe && cdGroupe === groupe.codeGroupeSubstance && cdSubs && cdSubs === 'XXX'
                        },
                        nodes: subNodes
                    }

                    nodes.push(node);
                }

                return nodes;
            },

            //Initialiser la catégorie
            initCategorie: function (type) {
                var select = $('#nom_inst');

                if (installation && installation !== '') {
                    select.val(decodeURIComponent(installation));
                }
            },


            //Initialiser les valeurs dans le select region
            initRegSelect: function (region) {
                var select = $("#region");
                var that = this;

                // Si options chargees
                if (!this.regions) {
                    // on charge les options
                    $.getJSON(
                        this.wsUrl + "/region",

                        function (regions) {
                            that.regions = regions;

                            // On remove toutes les valeurs du select deja existantes pour eviter la duplication
                            $.each(regions, function (i, region) {
                                select.append($("<option>").text(region.nomregion).val(region.coderegion));
                            });

                            if (region && region !== '') {
                                select.val(region);
                            }
                             select.niceSelect();
                        }
                    );
                }
            },


            //Initialiser les valeurs dans le select departement
            initDptSelect: function (region, departement) {
                var select = $('#departement');
                var that = this;
                select.niceSelect();
                if (region) {
                    // Si options non chargees
                    if (!this.departements[region]) {
                        // on charge les options
                        $.getJSON(
                            this.wsUrl + ("/departement/region/{id}".replace('{id}', region)),

                            function (departements) {
                                that.departements[region] = departements;

                                $.each(departements, function (i, departement) {
                                    select.append($("<option>").text(departement.nomdepartement+" ("+departement.codedepartement+")").val(departement.codedepartement));
                                });

                                if (departement && departement !== '') {
                                    select.val(departement);
                                }
                                select.niceSelect('update');
                            }
                        );
                    } else {
                        if ($('#departement option').length === 1) {
                            $.each(that.departements[region], function (i, departement) {
                                select.append($("<option>").text(departement.nomdepartement+" ("+departement.codedepartement+")").val(departement.codedepartement));
                            });
                            select.niceSelect('update');
                        }
                    }
                }
            },


            //Initialiser les valeurs dans le select commune
            initComSelect: function (departement, commune) {
                var select = $('#commune');
                var that = this;
                 select.niceSelect();
                if (departement) {
                    // Si options non chargees
                    if (!this.communes[departement]) {
                        // on charge les options
                        $.getJSON(
                            this.wsUrl + ("/commune/departement/{id}".replace('{id}', departement)),

                            function (communes) {
                                that.communes[departement] = communes;

                                $.each(communes, function (i, commune) {
                                    select.append($("<option>").val(commune.codecommune).text(commune.nomcommune));
                                });

                                if (commune && commune !== '') {
                                    select.val(commune);
                                }
                                select.niceSelect('update');
                            }
                        );
                    } else {
                        if ($('#commune option').length === 1) {
                            $.each(that.communes[departement], function (i, commune) {
                                select.append($("<option>").val(commune.codecommune).text(commune.nomcommune));
                            });
                            select.niceSelect('update');
                        }
                    }
                }
            },


            // Permet de recuperer les donnees en fonction de la valeur du select
            locationChanged: function (param) {
                var region = $('#region').val();
                var departement = $('#departement').val();
                var commune = $('#commune').val();
                var requestParam = '';
                var paramUrl = [];
                var url = location.hash.split('#/')[1] || '';

                url = url.split('&');
                paramUrl['page'] = '';

                for (var index in url) {
                    var aParam = url[index];
                    paramUrl[aParam.split('=')[0]] = aParam.split('=')[1];
                }

                if (param === 'commune') {
                    paramUrl['commune'] = commune;
                }

                if (param === 'departement') {
                    paramUrl['departement'] = departement;
                    delete paramUrl.commune;

                    $('#commune').find('option:gt(0)').remove();
                }

                if (param === 'region') {
                    paramUrl['region'] = region;

                    delete paramUrl.departement;
                    delete paramUrl.commune;

                    $('#commune').find('option:gt(0)').remove();
                    $('#departement').find('option:gt(0)').remove();
                }

                for (aParamUrl in paramUrl) {
                    if (paramUrl[aParamUrl] && paramUrl[aParamUrl] !== '') {
                        if (requestParam === '') {
                            requestParam = requestParam + aParamUrl + '=' + paramUrl[aParamUrl];
                        } else {
                            requestParam = requestParam + '&' + aParamUrl + '=' + paramUrl[aParamUrl];
                        }
                    }
                }

                this.setLocation(location.hash.split('#/')[0] + '#/' + requestParam);
            },

            informationChanged: function (param) {
                var type = getType();
                var requestParam = '';
                var paramUrl = [];
                var url = location.hash.split('#/')[1] || '';

                url = url.split('&');

                for (var index in url) {
                    var aParam = url[index];
                    paramUrl[aParam.split('=')[0]] = aParam.split('=')[1];
                }

                paramUrl['type'] = type;
                paramUrl['page'] = '';

                if (type === 'instruction') {
                    delete paramUrl['statut'];
                }

                for (aParamUrl in paramUrl) {
                    if (paramUrl[aParamUrl] && paramUrl[aParamUrl] !== '') {
                        if (requestParam === '') {
                            requestParam = requestParam + aParamUrl + '=' + paramUrl[aParamUrl];
                        } else {
                            requestParam = requestParam + '&' + aParamUrl + '=' + paramUrl[aParamUrl];
                        }
                    }
                }

                this.setLocation(location.hash.split('#/')[0] + '#/' + requestParam);
            },

            statutClassificationChanged: function(value) {
                var requestParam = '';
                var paramUrl = [];
                var url = location.hash.split('#/')[1] || '';

                url = url.split('&');

                for (var index in url) {
                    var aParam = url[index];
                    paramUrl[aParam.split('=')[0]] = aParam.split('=')[1];
                }

                paramUrl['statut'] = value;
                paramUrl['page'] = '';

                for (aParamUrl in paramUrl) {
                    if (paramUrl[aParamUrl] && paramUrl[aParamUrl] !== '') {
                        if (requestParam === '') {
                            requestParam = requestParam + aParamUrl + '=' + paramUrl[aParamUrl];
                        } else {
                            requestParam = requestParam + '&' + aParamUrl + '=' + paramUrl[aParamUrl];
                        }
                    }
                }

                this.setLocation(location.hash.split('#/')[0] + '#/' + requestParam);
            },

            nomEtablissementChanged: function(value) {
                var requestParam = '';
                var paramUrl = [];
                var url = location.hash.split('#/')[1] || '';

                url = url.split('&');

                for (var index in url) {
                    var aParam = url[index];
                    paramUrl[aParam.split('=')[0]] = aParam.split('=')[1];
                }

                if (value.trim()) {
                    paramUrl['nom'] = encodeURI(value);
                }
                else {
                    delete paramUrl['nom'];
                }

                paramUrl['page'] = '';

                for (aParamUrl in paramUrl) {
                    if (paramUrl[aParamUrl] && paramUrl[aParamUrl] !== '') {
                        if (requestParam === '') {
                            requestParam = requestParam + aParamUrl + '=' + paramUrl[aParamUrl];
                        } else {
                            requestParam = requestParam + '&' + aParamUrl + '=' + paramUrl[aParamUrl];
                        }
                    }
                }

                this.setLocation(location.hash.split('#/')[0] + '#/' + requestParam);
            },

            listePolluantsChanged(value) {
                var requestParam = '';
                var paramUrl = [];
                var url = location.hash.split('#/')[1] || '';

                url = url.split('&');

                for (var index in url) {
                    var aParam = url[index];
                    paramUrl[aParam.split('=')[0]] = aParam.split('=')[1];
                }

                if (!value) {
                    delete paramUrl['cdGroupe'];
                    delete paramUrl['cdSubs'];
                }
                else {
                    [cdGroupe, cdSubs] = value.split('::');
                    paramUrl['cdGroupe'] = cdGroupe;
                    paramUrl['cdSubs'] = cdSubs;
                }

                paramUrl['page'] = '';

                for (aParamUrl in paramUrl) {
                    if (paramUrl[aParamUrl] && paramUrl[aParamUrl] !== '') {
                        if (requestParam === '') {
                            requestParam = requestParam + aParamUrl + '=' + paramUrl[aParamUrl];
                        } else {
                            requestParam = requestParam + '&' + aParamUrl + '=' + paramUrl[aParamUrl];
                        }
                    }
                }

                this.setLocation(location.hash.split('#/')[0] + '#/' + requestParam);
            },

            reloadSites: function () {
                $('#firstSearch').val('true');
                loadSites(this);
                $('#firstSearch').val('false');
            },
        });
    });



    $(function () {
        app.run('#/data');

        $('#commune').change(function () {
            app.locationChanged('commune');
        });

        $("#region").change(function () {
            app.locationChanged('region');
            $('#departement').niceSelect('update');
            $('#commune').niceSelect('update');
        });

        $('#departement').change(function () {
            app.locationChanged('departement');
            $('#commune').niceSelect('update');
        });

        $('#instruction').click(function () {
            $('#isInstruction').val("true");
            $('#classificationStatut').hide();
            app.informationChanged('type');
        });

        $('#classification').click(function () {
            $('#isInstruction').val("false");
            $('#classificationStatut').show();
            app.informationChanged('type');
        });

        $('#classificationSis').click(function() {
            app.statutClassificationChanged('sis');
        });

        $('#classificationSup').click(function() {
            app.statutClassificationChanged('sup');
        });

        $('#nomSite').change(function() {
            var nom = $('#nomSite').val();
            app.nomEtablissementChanged(nom);
        });

        $('#listePolluants').change(function () {
            if ($('#listePolluants option').length === 0) {
                app.listePolluantsChanged(null);
            }
            else {
                value = $('#listePolluants option:nth-child(1)').val();
                app.listePolluantsChanged(value);
            }
        });

        $('#removePolluant').click(function() {
            $('#listePolluants option').remove();
            $('#listePolluants').change();
        })

        $('#go-resultId').on('click', function(e) {
            $('#go-resultId-error').html('');

            var idSite = $('input#idSite').val().trim();

            if (!idSite) {
                $('#go-resultId-error').html("<small>" + getJSONProperties()['erreurFormatIdentifiant'] + "</small>");
                return;
            }

            var url = location.hash.split('#/')[1];
            var paramUrl = {};

            if (url !== '') {
                url = url.split('&');

                for (var index in url) {
                    var param = url[index];
                    paramUrl[param.split('=')[0]] = param.split('=')[1];
                }
            }

            var type = paramUrl['type'];
            if (!type) {
                $('#go-resultId-error').html("<small>" + getJSONProperties()['erreurCategorisation'] + "</small>");
                return;
            }

            var url = wsUrlInfosolsSSP() + '/' + type + '/' + idSite;
            $.getJSON(url).done(function (res) {
                if (res.data && res.data.length > 0) {
                    window.open(getJSONProperties()['adresseFicheInfosols'] + type + '/' + res.data[0]['identifiantSsp'], '_blank');
                }
                else {
                    $('#go-resultId-error').html("<small>" + getJSONProperties()['aucunResultat'] + "</small>");
                }
            })
        });

        $('#go-result-infosols').on('click', function (e) {
            if ($("#instruction").hasClass("button-detail-on")) {
                var url = location.hash.split('#/')[1];
                var paramUrl = {};

                if (url !== '') {
                    url = url.split('&');

                    for (var index in url) {
                        var param = url[index];
                        paramUrl[param.split('=')[0]] = param.split('=')[1];
                    }
                }

                app.informationChanged(paramUrl['type']);
                app.reloadSites();
            }
            else if ($("#classification").hasClass("button-detail-on")) {
                if($("#classificationSis").hasClass("button-detail-on") || $("#classificationSup").hasClass("button-detail-on")) {
                    var url = location.hash.split('#/')[1];
                    var paramUrl = {};

                    if (url !== '') {
                        url = url.split('&');

                        for (var index in url) {
                            var param = url[index];
                            paramUrl[param.split('=')[0]] = param.split('=')[1];
                        }
                    }

                    app.informationChanged(paramUrl['type']);
                    app.reloadSites();
                }
                else {
                    $('#sammyListeResultatInfosols').html('<h3>' + getJSONProperties()['erreurSousCategorie'] + "</h3>");
                }
            }
            else {
                $('#sammyListeResultatInfosols').html('<h3>' + getJSONProperties()['erreurCategorisation'] + "</h3>");
            }

            $('html, body').animate({
                scrollTop: ($("#risque-search-result").offset().top) - 200
            }, 500);
        });
    });
  })(jQuery);
```