# Distribution

Frankenstein packages and repository databases are signed with an OpenPGP
signing key. Package installation remains inert; `frankenstein setup` is still
required after pacman installs the packages.

## Signing-key storage

Set `GNUPGHOME` explicitly before running any repository command. The build
script refuses to use the default user keyring. For a real release, keep the
private key in an access-controlled offline location outside the Git checkout
and unlock it only for signing. Back up and protect that location separately.

The VM workflow uses a disposable, unencrypted test key under
`.signing/test-repository/`. That directory is ignored by Git and must never be
published or reused for a real release:

```bash
fingerprint=$(packaging/repository/create-test-key.sh \
  .signing/test-repository)
export GNUPGHOME=$PWD/.signing/test-repository
```

Only the armored public key and its full fingerprint are copied into a
repository.

## Build a signed repository

Build packages first, then pass their paths and the full signing-key
fingerprint:

```bash
packaging/arch/build.sh --cleanbuild --force --noconfirm
packaging/repository/build.sh \
  --key "$fingerprint" \
  --output dist/frankenstein \
  packaging/arch/packages/frankenstein-core-*.pkg.tar.zst \
  packaging/arch/packages/frankenstein-kde-*.pkg.tar.zst
```

The output contains detached package signatures, a signed
`frankenstein.db`, a signed `frankenstein.files` database, the public key, its
fingerprint, and SHA-256 checksums. Verify the manifest and signatures before
copying the repository:

```bash
(cd dist/frankenstein && sha256sum --check SHA256SUMS)
gpg --verify \
  dist/frankenstein/x86_64/frankenstein.db.tar.gz.sig \
  dist/frankenstein/x86_64/frankenstein.db.tar.gz
```

## Establish trust on an Omarchy machine

Transfer the repository and `frankenstein-repository.asc` through a trusted
channel. Compare the complete fingerprint with an independently obtained
value before trusting it:

```bash
gpg --show-keys --with-fingerprint frankenstein-repository.asc
sudo pacman-key --add frankenstein-repository.asc
sudo pacman-key --finger <FULL_FINGERPRINT>
sudo pacman-key --lsign-key <FULL_FINGERPRINT>
```

Add the repository after the fingerprint is verified:

```ini
[frankenstein]
SigLevel = Required DatabaseRequired
Server = https://example.invalid/frankenstein/$arch
```

Then synchronize and install:

```bash
sudo pacman -Sy
sudo pacman -S frankenstein-core frankenstein-kde
frankenstein preflight
frankenstein setup
```

For normal full-system upgrades, use Omarchy's supported update entry point:

```bash
omarchy update
```

The VM integration test exercises a direct `pacman -Syu` only with Omarchy's
explicit `OMARCHY_ALLOW_DIRECT_PACMAN=1` test override.

The example URL is intentionally invalid. This repository has not been
published, and no signing-key trust has been added to the development host.
