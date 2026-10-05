import json
from pathlib import Path
import tempfile
import unittest
from omasteamdeck.core import State, discover_apps, discover_games, desktop_command

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_profiles_persist_and_isolate(self):
        path=self.root/'state.json'; state=State(path)
        state.data['profiles'][0]['favorites'].append('youtube')
        self.assertTrue(state.add_profile('Andrew'))
        self.assertFalse(state.add_profile(' andrew ')); self.assertFalse(state.add_profile(' '))
        loaded=State(path)
        self.assertEqual(loaded.data['profiles'][0]['favorites'],['youtube'])
        self.assertEqual(loaded.data['profiles'][1]['favorites'],[])
    def test_corrupt_state_falls_back(self):
        p=self.root/'state.json'
        for data in ('{broken','[]','null','{"profiles":[]}','{"profiles":[null]}'):
            p.write_text(data); self.assertEqual(State(p).data['profiles'][0]['name'],'Player 1')
    def test_discover_external_steam_library_and_deduplicate(self):
        primary=self.root/'.local/share/Steam/steamapps'; primary.mkdir(parents=True)
        external=self.root/'Games SSD'; (external/'steamapps').mkdir(parents=True)
        (primary/'libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "'+str(external)+'" } }')
        manifest='"AppState" { "appid" "123" "name" "A Great Game" }'
        (primary/'appmanifest_123.acf').write_text(manifest)
        (external/'steamapps/appmanifest_123.acf').write_text(manifest)
        games=discover_games(self.root); self.assertEqual(len(games),1); self.assertEqual(games[0].target,'steam://rungameid/123')
    def test_desktop_visibility_overrides_and_literal_arguments(self):
        user=self.root/'user'; system=self.root/'system'; user.mkdir(); system.mkdir()
        (system/'hidden.desktop').write_text('[Desktop Entry]\nType=Application\nName=Hidden\nExec=true\n')
        (user/'hidden.desktop').write_text('[Desktop Entry]\nHidden=true\n')
        p=system/'test.desktop'; p.write_text('[Desktop Entry]\nType=Application\nName=Example\nExec=/bin/echo "two words" %U %c %i %%\nIcon=example\n')
        (system/'terminal.desktop').write_text('[Desktop Entry]\nType=Application\nName=Terminal\nExec=true\nTerminal=true\n')
        self.assertEqual([i.name for i in discover_apps([user,system])],['Example'])
        self.assertEqual(desktop_command(p)[0],['/bin/echo','two words','Example','--icon','example','%'])

    def test_malformed_catalog_file_does_not_abort_discovery(self):
        apps=self.root/'apps'; apps.mkdir()
        (apps/'broken.desktop').write_bytes(b'\xff\xfe')
        self.assertEqual(discover_apps([apps]),[])
        steam=self.root/'.local/share/Steam/steamapps'; steam.mkdir(parents=True)
        (steam/'libraryfolders.vdf').write_bytes(b'\xff\xfe')
        (steam/'appmanifest_123.acf').write_bytes(b'\xff\xfe')
        self.assertEqual(discover_games(self.root),[])

if __name__=='__main__': unittest.main()
