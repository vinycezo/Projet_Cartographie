"""Export Qlik source and destination variables to Excel."""

import argparse
import codecs
from itertools import product
from pathlib import Path

from qlik_script_extractor import QlikScriptExtractor
from variable_resolver import VariableResolver


HEADERS = (
    "Application", "Input", "Valeur_variable_input", "output", "Valeur_variable_output",
)
EMPTY_VARIABLE = (None, None)


def read_script(path):
    data = path.read_bytes()
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def application_rows(path):
    extractor = QlikScriptExtractor(VariableResolver())
    inventory = extractor.build_table_inventory(read_script(path), include_variables=True)
    pairs = {}
    application_inputs = {}
    application_outputs = {}
    for details in inventory.values():
        inputs = dict.fromkeys(
            variable for source in details["sources"] for variable in source["variables"]
        )
        outputs = dict.fromkeys(details.get("output_variables", ()))
        application_inputs.update(inputs)
        application_outputs.update(outputs)
        if inputs or outputs:
            pairs.update(dict.fromkeys(product(
                inputs or (EMPTY_VARIABLE,), outputs or (EMPTY_VARIABLE,),
            )))

    common_input = next(iter(application_inputs)) if len(application_inputs) == 1 else EMPTY_VARIABLE
    common_output = next(iter(application_outputs)) if len(application_outputs) == 1 else EMPTY_VARIABLE
    application_pairs = dict.fromkeys(
        (
            common_input if input_variable == EMPTY_VARIABLE else input_variable,
            common_output if output_variable == EMPTY_VARIABLE else output_variable,
        )
        for input_variable, output_variable in pairs
    )
    complete_inputs = {inp for inp, out in application_pairs if out != EMPTY_VARIABLE}
    complete_outputs = {out for inp, out in application_pairs if inp != EMPTY_VARIABLE}
    for input_variable, output_variable in application_pairs or ((EMPTY_VARIABLE, EMPTY_VARIABLE),):
        if input_variable == EMPTY_VARIABLE and output_variable in complete_outputs:
            continue
        if output_variable == EMPTY_VARIABLE and input_variable in complete_inputs:
            continue
        yield (path.stem, *input_variable, *output_variable)


def export_workbook(scripts, destination):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Variables"
    workbook.create_sheet("Feuille 2")
    sheet.append(HEADERS)
    for script in scripts:
        for row in application_rows(script):
            sheet.append(row)
            for cell in sheet[sheet.max_row]:
                if cell.value is not None:
                    cell.data_type = "s"

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, width in enumerate((42, 24, 55, 24, 55), start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    workbook.save(destination)
    return sheet.max_row - 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Folder of .qvs scripts, or one .qvs or .txt file")
    parser.add_argument("-o", "--output", type=Path, default=Path("cartographie.xlsx"))
    args = parser.parse_args()

    if args.source.is_dir():
        scripts = sorted(
            path for path in args.source.iterdir()
            if path.is_file() and path.suffix.lower() == ".qvs"
        )
    elif args.source.is_file() and args.source.suffix.lower() in {".qvs", ".txt"}:
        scripts = [args.source]
    else:
        parser.error(f"Expected a script folder or a .qvs or .txt file: {args.source}")

    if not scripts:
        parser.error(f"No .qvs scripts found in {args.source}")
    if args.output.suffix.lower() != ".xlsx":
        parser.error("Output filename must end in .xlsx")
    try:
        rows = export_workbook(scripts, args.output)
    except ModuleNotFoundError as error:
        if error.name != "openpyxl":
            raise
        parser.exit(1, "Install the Excel dependency with: python -m pip install openpyxl\n")
    except (OSError, UnicodeError) as error:
        parser.exit(1, f"Export failed: {error}\n")
    print(f"Exported {rows} rows from {len(scripts)} scripts to {args.output}")


if __name__ == "__main__":
    main()
