import typer
from cli.commands.banatic import app as banatic_app
from cli.commands.base_functions import app as base_functions_app
from cli.commands.bdtopo import app as bdtopo_app
from cli.commands.bpe import app as bpe_app
from cli.commands.cadastre import app as cadastre_app
from cli.commands.cartofriches import app as cartofriches_app
from cli.commands.docurba import app as docurba_app
from cli.commands.dvf import app as dvf_app
from cli.commands.geoportail import app as geoportail_app
from cli.commands.georisques import app as georisques_app
from cli.commands.geosirene import app as geosirene_app
from cli.commands.logement import app as logement_app
from cli.commands.ocsge import app as ocsge_app
from cli.commands.patrimoine import app as patrimoine_app

app = typer.Typer()

app.add_typer(base_functions_app)
app.add_typer(dvf_app)
app.add_typer(cadastre_app)
app.add_typer(logement_app)
app.add_typer(georisques_app)
app.add_typer(geoportail_app)
app.add_typer(banatic_app)
app.add_typer(bdtopo_app)
app.add_typer(ocsge_app)
app.add_typer(docurba_app)
app.add_typer(bpe_app)
app.add_typer(patrimoine_app)
app.add_typer(geosirene_app)
app.add_typer(cartofriches_app)
