import sys
import click


@click.group(invoke_without_command=True)
@click.option("--a", default="a string")
@click.option("--b", default=2)
@click.option("--c", default=False)
@click.pass_context
def cli(ctx, a, b, c):
    if ctx.invoked_subcommand is None:
        click.echo("I was invoked without subcommand")
        ctx.ensure_object(dict)
        ctx.obj["a"] = a
        ctx.obj["b"] = b
        ctx.obj["c"] = c
        click.echo("Running A from cli")
        A(ctx)
        click.echo("Running B from cli")
        B(ctx)
    else:
        click.echo("I am about to invoke %s" % ctx.invoked_subcommand)


@cli.command()
@click.pass_context
def A(ctx):
    click.echo("Got into A")
    a = ctx.obj["a"]
    b = ctx.obj["b"]
    c = ctx.obj["c"]
    click.echo("Function A")
    click.echo(a, b, c)


@cli.command()
@click.option("--a", default="a string")
@click.option("--b", default=2)
@click.option("--c", default=False)
@click.pass_context
def B(ctx):
    click.echo("Function B")
    click.echo(a, b, c)


if __name__ == "__main__":
    print(click.__version__)
    cli()
