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
            version = "0.2.0";
            pyproject = true;
            src = self;
            build-system = [ pkgs.python312Packages.setuptools ];
            dependencies = with pkgs.python312Packages; [
              markdown-it-py
              wcwidth
            ];
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
                ]
              ))
              pkgs.ruff
              pkgs.nixfmt-rfc-style
            ];
          };
        }
      );
      checks = forEachSystem (system: {
        package = self.packages.${system}.default;
      });
    };
}
