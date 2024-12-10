# %%
from pathlib import Path

from prefect import flow, task

from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path


@task
def import_rga_shape(files, schema="public", table="risques_rga"):
    for file in files:
        print("Importing file: ", file)
        import_shapefile(
            file=file,
            table=table,
            source_srs="EPSG:2154",
            destination_srs="EPSG:2154",
            schema=schema,
        )


@flow(name="import Risque Retrait-Gonflement des Argiles")
def import_rga_flow(path, schema="public"):
    files = list_files_at_path(path, r"AleaRG.*", extension=".shp")
    import_rga_shape(files, schema)


# %%
import_rga_flow._run(path=Path("/Users/thomasbrosset/Downloads/mvt"))
# %%
