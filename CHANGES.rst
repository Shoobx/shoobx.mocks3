=========
CHANGELOG
=========


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
