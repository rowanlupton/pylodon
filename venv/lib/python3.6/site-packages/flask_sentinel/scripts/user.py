# -*- coding: utf-8 -*-
"""
    flask-sentinel.user
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import click

from ..data import Storage

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])



@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """ User management script """


@cli.command()
@click.option('--user', '-u', prompt='Username', help='Username')
@click.option('--password', '-p', prompt='Password', confirmation_prompt=True,
              hide_input=True, help='User password')
def create(user, password):
    """ create a user """

    Storage.db_name = 'oauth'
    Storage.save_user(user, password)


@cli.command()
def delete(user):
    """ delete a user """
    click.echo('deleting!')


if __name__ == '__main__':
    cli()
