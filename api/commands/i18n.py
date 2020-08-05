import json
import click
import re
import os

from flask.cli import AppGroup
from src import BASE_DIR, db
from src.i18n.models import I18NLocale, I18NKey, I18NValue


def validate_locale(ctx, param, value):
    if not re.fullmatch('[a-z]{2}-[A-Z]{2}', value):
        raise click.BadParameter(
            f"{value} is not a valid locale code. It must be in the form of ab-XY")
    return value


def create_dir(ctx, param, value):
    pardir = os.path.dirname(value.name)
    if pardir:
        os.makedirs(pardir, exist_ok=True)
    return value


def default_target():
    params = click.get_current_context().params
    if 'locale' not in params:
        click.echo(
            "Can't get default target from the specified <locale> parameter")
        raise click.Abort
    locale = params['locale']
    return os.path.join(BASE_DIR, 'i18n', f"{locale}.json")


def tree_to_list(tree, is_leaf=lambda node: isinstance(node, str)):
    """ convert a tree into a list of { 'path': 'abc.xyz', 'value': leaf_node }
    where is_leaf(leaf_node) == True
    """
    result = []

    def tree_to_list_helper(word_map, path=[]):
        for key, val in word_map.items():
            if (is_leaf(val)):
                result.append({'path': path + [key], 'value': val})
            else:
                tree_to_list_helper(val, path + [key])
    tree_to_list_helper(tree)
    return result


def list_to_tree(entries):
    """ convert a list of { 'path': 'abc.xyz', 'value': node } into a tree
    {
      'abc': {
        'xyz': node
      }
    }
    """
    tree = {}
    for entry in entries:
        keys = entry['path'].split('.')
        t = tree
        but_last, last = keys[:-1], keys[-1]
        for key in but_last:
            t = t.setdefault(key, {})
        if last in t:
            raise RuntimeError(
                f"{entry['path']} already exists: '{t[last]}', won't set to '{entry['value']}'")
        t[last] = entry['value']
    return tree


def create_i18n_cli(app):
    i18n_cli = AppGroup('i18n', help="Maintain translation entries.")

    @i18n_cli.command('load')
    @click.argument('locale', callback=validate_locale, metavar="<locale>")
    @click.option('--override/--no-override', default=True,
                  show_default=True,
                  help="Override if value already exists")
    @click.option('--target',
                  default=default_target,
                  show_default=os.path.join(BASE_DIR, 'i18n', "<locale>.json"),
                  type=click.File("r"),
                  help="The source file to load values from")
    def import_values(locale, target, override):
        """ Load values from a json file into the database.

        <locale>: the locale code of the processed values. E.g. en-US """
        entry_count = 0
        locale_name = locale
        click.echo(f"loading values from [{target.name}]")
        tree = json.load(target)

        def is_leaf(node):
            return isinstance(
                node, dict) and 'gloss' in node and isinstance(
                node['gloss'], str)

        entries = tree_to_list(tree, is_leaf=is_leaf)
        locale = db.session.query(I18NLocale).filter_by(code=locale).first()
        if not locale:
            click.echo(
                f"locale [{locale_name}] does not exist in database, creating one")
            locale = I18NLocale(
                code=locale_name,
                desc="")
            db.session.add(locale)
            db.session.commit()
        for entry in entries:
            key_id = '.'.join(entry['path'])
            key = db.session.query(I18NKey).filter_by(id=key_id).first()
            if not key:
                click.echo(
                    f"key [{key_id}] does not exist in database, creating one")
                key = I18NKey(
                    id=key_id,
                    desc="")
                db.session.add(key)
            value = db.session.query(I18NValue).filter_by(
                key_id=key.id, locale_code=locale.code).first()
            if value:
                if override:
                    value.gloss = entry['value']['gloss']
                    value.verified = entry['value']['verified']
                else:
                    continue
            else:
                value = I18NValue(
                    gloss=entry['value']['gloss'],
                    verified=entry['value']['verified'],
                    key_id=key.id,
                    locale_code=locale.code
                )
            db.session.add(value)
            entry_count += 1
        db.session.commit()
        click.echo("Successfully loaded data into the database")
        click.echo(f"Source file: {target.name}")
        click.echo(f"Locale:      {locale_name}")
        click.echo(f"Entry count: {entry_count}")

    @i18n_cli.command('dump')
    @click.argument('locale', callback=validate_locale, metavar="<locale>")
    @click.option('--target',
                  default=default_target,
                  show_default=os.path.join(BASE_DIR, 'i18n', "<locale>.json"),
                  callback=create_dir,
                  type=click.File("w"),
                  help="The destination file to dump values to")
    def export_values(locale, target):
        """ Dump values from the database into a json file.

        <locale>: the locale code of the processed values. E.g. en-US """
        click.echo(f"dumping values into {target.name}")
        values = db.session.query(I18NValue).filter_by(
            locale_code=locale).all()
        entries = map(
            lambda value: {
                'path': value.key_id,
                'value': {
                    'gloss': value.gloss,
                    'verified': value.verified
                }
            }, values)
        tree = list_to_tree(entries)
        json.dump(tree, target, indent=2, sort_keys=True)
        click.echo("Successfully dumped data from the database")
        click.echo(f"Target file: {target.name}")
        click.echo(f"Locale:      {locale}")
        click.echo(f"Entry count: {len(values)}")

    @i18n_cli.command('load-descriptions')
    @click.option('--override/--no-override',
                  default=False,
                  show_default=True,
                  help="Override if descriptions is non-empty")
    @click.option('--target',
                  default=os.path.join(BASE_DIR, 'i18n', "_desc.json"),
                  show_default=True,
                  type=click.File("r"),
                  help="The source file to load descriptions from")
    def import_descriptions(target, override):
        """ Load descriptions from a json file into the database. """
        entry_count = 0
        skip_count = 0
        tree = json.load(target)
        entries = tree_to_list(tree)
        click.echo(f"loading descriptions from [{target.name}]")
        for entry in entries:
            key_id = '.'.join(entry['path'])
            key = db.session.query(I18NKey).filter_by(id=key_id).first()
            description = entry['value']
            if not key:
                click.echo(
                    f"key [{key_id}] does not exist in database, creating one with description [{description}]")
                key = I18NKey(
                    id=key_id,
                    desc=description)
            elif key.desc and not override:  # if description non-empty and not overriding
                click.echo(
                    f"key [{key_id}] already has description [{key.desc}], not overriding with [{description}]")
                skip_count += 1
                continue
            else:
                key.desc = description
            db.session.add(key)
            entry_count += 1
        db.session.commit()
        click.echo("Successfully loaded descriptions into the database")
        click.echo(f"Source file: {target.name}")
        click.echo(f"Entry count: {entry_count}")
        click.echo(f"Skip count: {skip_count}")
        if skip_count:
            click.echo(
                "Hint: use --override to load descriptions even if they exist")

    @i18n_cli.command('dump-descriptions')
    @click.option('--dump-empty/--no-dump-empty',
                  default=False,
                  show_default=True,
                  help="Dump description even if it is empty "
                  "(can be useful when want to retrieve a complete list of keys)")
    @click.option('--empty-placeholder', default="", show_default=True,
                  help="The description to use when the description in database is not given or empty,"
                  " must be used with --dump-empty to take effect")
    @click.option('--target',
                  default=os.path.join(BASE_DIR, 'i18n', "_desc.json"),
                  show_default=True,
                  callback=create_dir,
                  type=click.File("w"),
                  help="The destination file to dump descriptions to")
    def export_descriptions(target, dump_empty, empty_placeholder):
        query = db.session.query(I18NKey)
        if not dump_empty:
            query = query.filter(I18NKey.desc != None).filter(I18NKey.desc != "")
        keys = query.all()

        entries = map(
            lambda key: {
                'path': key.id,
                'value': key.desc or empty_placeholder
            }, keys)
        tree = list_to_tree(entries)
        json.dump(tree, target, indent=2, sort_keys=True)
        click.echo("Successfully dumped data from the database")
        click.echo(f"Target file: {target.name}")
        click.echo(f"Entry count: {len(keys)}")

    app.cli.add_command(i18n_cli)
