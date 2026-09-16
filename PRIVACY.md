# Privacy

Last updated 2026-09-16.

## The short version

The software in this repository collects nothing about you, sends nothing
about you anywhere, and makes no outbound request at all. There is no
telemetry, no analytics, no crash reporting, no licence check and no
phone-home of any kind.

That is not a policy promise you have to take on trust, which is the only
reason it is worth writing down. This software fetches no market data by
design: it computes over files you give it. There is no provider to call,
no key to store, and no account to have.

Two things this section does not cover, both below: the separate hosted
service at `riskdesk.avidquant.com`, and what happens when you choose to
send data to an AI agent.

## What runs where

Everything in this repository runs on your own machine: the `riskdesk`
command line, the local MCP server, the dashboard, and the ORE adapter.
They are local processes you start.

The dashboard binds a loopback address and refuses any other host, so it
serves your machine and nothing else. It embeds its own styling and charts
rather than loading them, so opening a page makes no third-party request,
and it sends a content security policy of `default-src 'none'` that tells
the browser to refuse one. There is no authentication because there is
nothing to authenticate to; that is also why it will not bind a public
interface.

## What leaves your machine

From this repository, at runtime: nothing.

The only network access in the project is `pip`, during installation,
fetching packages from the index you configure. After that the tools run
with no network at all. A test in the suite watches for an outbound
connection while the dashboard serves and fails if one is made.

## What is stored on your machine

Whatever you tell a command to write, and nothing else.

`riskdesk report --output PATH` writes one HTML file where you say. The
ORE adapter writes its outputs into the directory you name, which it
requires to be new and outside the input project. Nothing is written to a
hidden location, no cache is kept between runs, and no history is
recorded. Delete the files and nothing remains.

Your inputs are read and not copied. The result envelope records a
SHA-256 of the input so you can tell which file produced which number; a
hash is not the file and cannot be turned back into it.

## The hosted service

`riskdesk.avidquant.com` is a separate service with its own repository,
its own deployment and its own policy. **This repository ships only the
client side of it**: the `risk-desk-hosted` plugin is manifests and skill
files that tell an agent where the endpoint is. No code here runs there.

What the service states about data it receives, which you should confirm
against its own policy rather than this file:

- It accepts position and P&L data through a browser upload.
- It holds that data in memory for one hour.
- It writes none of it to disk.
- It discards it on delete, or when the hour expires.

Its public report uses synthetic data and needs no login. It cannot run
`risk_xva` at all, because that reads an ORE project directory on your own
machine, which a remote service cannot see.

If you are weighing whether to use it: the local plugin computes on your
machine and sends nothing anywhere, and for real positions it is the
better choice. That is the recommendation the hosted plugin's own README
makes as well.

## What an AI agent changes

This project is built to be driven by an agent, and that is the one path
where your data can leave your machine without this software sending it.

When you ask a model to analyse a position file, the contents go to
whoever runs that model, under their terms and their retention policy, not
this project's. That is true of the local plugin too: the plugin runs
locally, but the conversation does not. A local MCP server means the
computation is local; it does not mean the transcript is.

`data_mode` records what you declared about your rights to an input. It is
your declaration, not a rights certificate, and nothing in this software
checks it or acts on it beyond writing it into the result.

If you cannot send a file to a third party, do not put it in a
conversation with one.

## The issue tracker

Issues and pull requests are public and permanent. Do not paste a real
position file, a real P&L series, or anything derived from a licensed
feed. Reduce it to the smallest synthetic case that still reproduces; every
file in `examples/` is synthetic and says so in its own `source` field.

## Changes

This document describes the software in this repository as it stands at
the commit you are reading. If the behaviour changes, this file changes in
the same commit, and CHANGELOG.md records it.
