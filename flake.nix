{
  description = "A Herdr popup for reading completed AI replies";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSystem = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forEachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.python312Packages.buildPythonApplication {
            pname = "herdr-speed-read";
            version = "0.5.1";
            pyproject = true;
            src = self;
            build-system = [ pkgs.python312Packages.setuptools ];
            dependencies = with pkgs.python312Packages; [
              markdown-it-py
              wcwidth
              pygobject3
              pycairo
            ];
            nativeBuildInputs = [
              pkgs.gobject-introspection
              pkgs.wrapGAppsNoGuiHook
            ];
            buildInputs = [ pkgs.pango ];
            FONTCONFIG_FILE = pkgs.makeFontsConf {
              fontDirectories = [
                pkgs.dejavu_fonts
                pkgs.noto-fonts-cjk-sans
                pkgs.noto-fonts-color-emoji
              ];
            };
            preFixup = ''
              gappsWrapperArgs+=(--set FONTCONFIG_FILE "$FONTCONFIG_FILE")
            '';
            nativeCheckInputs = [ pkgs.python312Packages.pytestCheckHook ];
            pythonImportsCheck = [ "herdr_speed_read" ];
            postInstall = ''
              mkdir -p "$out/share/herdr-plugin"
              substitute ${./herdr-plugin.toml} "$out/share/herdr-plugin/herdr-plugin.toml" \
                --replace-fail './.plugin-build/bin/herdr-speed-read' "$out/bin/herdr-speed-read"
            '';
          };
        }
      );
      devShells = forEachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python312.withPackages (
                packages: with packages; [
                  pytest
                  markdown-it-py
                  wcwidth
                  pygobject3
                  pycairo
                ]
              ))
              pkgs.gobject-introspection
              pkgs.pango
              pkgs.ruff
              pkgs.nixfmt-rfc-style
            ];
            FONTCONFIG_FILE = pkgs.makeFontsConf {
              fontDirectories = [
                pkgs.dejavu_fonts
                pkgs.noto-fonts-cjk-sans
                pkgs.noto-fonts-color-emoji
              ];
            };
          };
        }
      );
      checks = forEachSystem (system: {
        package = self.packages.${system}.default;
      });
    };
}
