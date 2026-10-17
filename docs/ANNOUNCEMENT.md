# Announcement drafts

Draft copy for a release announcement; not a report of a published post.
Link to the repository/release and invite setup feedback. Do not add private
project references, screenshots, infrastructure details or unsupported benchmarks.

## English — technical community

We have released **dokploy-actions-runner**, an open-source Dokploy template for
self-hosted GitHub Actions runners, maintained by Simplarix.

It supports repository and organization configuration, independent runner names,
labels and existing groups, plus explicit environment forwarding and startup
validation. Defaults run as non-root without privileged mode or a host Docker
socket. It uses the maintained myoung34 runner image rather than a custom runner.

We have used the repository-runner path successfully in Dokploy for real CI jobs
and after Stop → Deploy. Automated checks cover configuration and mocked lifecycle
behavior. The documentation lists the remaining live-validation limits.

It is intended for trusted workflows; Docker-dependent jobs need a separate
environment. You can keep GitHub-hosted runners for other jobs in the same workflow.

Code, examples and setup: https://github.com/Simplarix/dokploy-actions-runner

If you use Dokploy, we would appreciate feedback on setup and workflow
compatibility. Please omit tokens and private environment details from reports.

## Deutsch — Simplarix / LinkedIn

Wir haben eine kleine Open-Source-Lösung veröffentlicht:
**dokploy-actions-runner** bringt selbst gehostete GitHub Actions Runner nach
Dokploy – mit eigener Konfiguration pro Deployment, geprüften Pflichtangaben und
ohne privilegierten Modus oder Zugriff auf den Docker-Socket des Hosts.

Die Vorlage wird von Simplarix gepflegt und nutzt ein etabliertes Runner-Image.
Den Repository-Betrieb haben wir mit echten CI-Jobs und nach Stop → Deploy
praktisch erprobt. Unterstützte Workloads und noch offene Live-Prüfungen stehen
transparent in der Dokumentation.

Ein möglicher Einsatz: geeignete lange Jobs auf eigener Infrastruktur ausführen
und andere Jobs weiterhin bei GitHub lassen. Wie viel das spart oder beschleunigt,
hängt von Workload, Hardware und Auslastung ab.

Repository und Anleitung: https://github.com/Simplarix/dokploy-actions-runner

Wer Dokploy nutzt: Wir freuen uns über Rückmeldungen zur Einrichtung und zu
passenden Workflows.
