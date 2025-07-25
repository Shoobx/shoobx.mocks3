=========
CHANGELOG
=========


5.0.1 (unreleased)
------------------

- Nothing changed yet.


5.0.0 (2025-07-25)
------------------

- Update to moto 5.0
- Remove python 3.8 support


4.2.14 (2025-06-12)
-------------------

- Fix chunked uploads by backporting chunked decode from 5.0


4.2.12 (2025-04-28)
-------------------

- 4.2.11 re-release


4.2.11 (2025-04-28)
-------------------

- Rename importlib to avoid problem with metadata attibute override


4.2.10 (2025-02-27)
-------------------

- Upgrade project metadata to pyproject.toml
- Replace pkg_resources with importlib


4.2.8.1 (2024-10-11)
--------------------

- Lock cache for apt for multiartch build


4.2.8 (2024-10-09)
------------------

- Make docker image smaller
- Fix image permissions


4.2.7 (2024-02-25)
------------------

- Fix broken pre-release.


4.2.6 (2024-02-25)
------------------

- Updates to mooto 4.2.14.


4.2.5 (2023-08-23)
------------------

- Update to moto.


4.2.4 (2023-07-29)
------------------

- Updates to moto and boto.


4.2.3 (2023-06-26)
------------------

- Add checksum attributes to class Key


4.2.2 (2023-03-21)
------------------

- Add parameter to put_object.


4.2.1 (2023-03-12)
------------------

- Fix issue when environment variables would only differ by case.


4.2.0 (2023-02-21)
------------------

- Revert licence changes
- Compatibility with moto 4.1.3
- werkzeug 2.2.3 works again
- moto 4.1.1 works, but 4.1.2 not
- Moving CI to github actions
- Added python 3.11 testing and compatibility
- Removed python 3.7 compatibility


4.1.1 (2023-01-24)
------------------

- Fixed license classifier.


4.1.0 (2023-01-24)
------------------

- Released under ZPL2.1


4.0.1 (2022-12-09)
------------------

- Compatibility with moto 4.0.11


4.0.0 (2022-09-20)
------------------

-  Upgrade to moto4.


3.1.4 (2022-08-03)
------------------

- Pin Werkzeug to 2.1.2 as >=2.2.0 doesn't work with moto.


3.1.3 (2022-07-08)
------------------

- Compatibility with moto 3.1.16
- Properly fix s3 backends/responses


3.1.2 (2022-06-23)
------------------

- Compatibility with moto 3.1.14


3.1.1 (2022-06-08)
------------------

- Compatibility with moto 3.1.12


3.1.0 (2022-05-20)
------------------

- Compatibility with moto 3.1.9


3.0.0 (2022-01-21)
------------------

- Compatibility with moto 3.0.0


2.1.0 (2022-01-21)
------------------

- Compatibility with moto 2.3.2

- Fix tox config, dropping Py2.7 and PyPy, adding Py3.10.


2.0.0 (2022-01-06)
------------------

- Compatibility with moto 2.2.20


1.6.1 (2021-07-22)
------------------

- Added `log-file` config option.


1.6.0 (2021-05-11)
------------------

- Upgraded to latest pkgs including moto 2.0.5, added py3.9

- Ported all tests to boto3 and removed boto support

- Fixed bucket lifecycle cfg

1.5.0 (2020-12-01)
------------------

- Upgraded to latest pkgs including moto 1.3.16, py3 is now default.


1.4.2 (2018-03-16)
------------------

- Another small tweak needed to work in new moto. A key now always expects
  an ACL.


1.4.1 (2018-03-12)
------------------

- Tweak server startup to work with new moto APIs. Added test to verify app
  configuration works.


1.4.0 (2018-03-12)
------------------

- Upgraded to support `moto == 1.2.0`.


1.3.0 (2018-02-03)
------------------

- Use `flask_cors` to inject the proper access control headers. This way not
  only the handled HTTP methods will put the CORS headers in the response, but
  OPTIONS -- which is used by browsers to check the CORS settings - will also
  receive the headers.


1.2.0 (2017-05-23)
------------------

- Add support for Python 3.5, 3.6 and PyPy.


1.1.0 (2017-05-23)
------------------

- First public release.

- Switched to commuity tools: tox, Travis CI and Coveralls.io


1.0.1 (2017-05-15)
------------------

- Add Makefile to release.


1.0.0 (2017-05-15)
------------------

- Initial release.
