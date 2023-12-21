from __future__ import annotations

import json
import logging

from aiohttp_requests import requests

from background_tasks.base import CrontabDiscordTask

logger = logging.getLogger(__name__)

FACTION_LOOKUP = {
    'Irregular Militia Forces': 'MIL',
    "People's Liberation Army": 'PLA',
    'PLA Navy Marine Corps': 'PLANMC',
    'Russian Airborne Forces': 'VDV',
    'Canadian Armed Forces': 'CAF',
    'British Armed Forces': 'GB',
    'Australian Defence Force': 'AU',
    'Russian Ground Forces': 'RU',
    'United States Army': 'US',
    'United States Marine Corps': 'USMC',
    'Insurgent Forces': 'INS',
    'Middle Eastern Alliance': 'MEA',
    'Turkish Land Forces': 'TLF',
}
VEHICLES_LOOKUP = {
    # MBTs
    'FV4034': 'MBT',
    'Leopard 2A6M CAN': 'MBT',
    'M1A1': 'MBT',
    'M1A2': 'MBT',
    'T-62' 'T-72B3': 'MBT',
    'T-72S': 'MBT',
    'ZTZ99A': 'MBT',
    'M60T': 'MBT',
    # IFVs
    'ASLAV': 'LAV',
    'BMD-1M IFV': 'BMD-1M',
    'BMD-4M IFV': 'BMD-4M',
    'BMP-2': 'BMP-2',
    'BMP-1': 'BMP-1',
    'Coyote': 'Coyote',
    'FV510 UA': 'FV510 UA',
    'FV510': 'FV510',
    'FV520 CTAS40': 'CTAS',
    'LAV 6': 'LAV',
    'M2A3': 'Bradley',
    'MT-LBM 6MB': 'MT-LBM 6MB',
    'ZBD04A': 'ZBD',
    'ZBD05 HJ73C IFV': 'ZBD',
    'ZBD05 IFV': 'ZBD',
    'ZBD05': 'ZBD',
    'ZBL08 HJ73C IFV': 'ZBL',
    'ZBL08 HJ73C': 'ZBL',
    'ZBL08 IFV': 'ZBL',
    'ZBL08': 'ZBL',
    'PARS III 25mm': 'PARS 25mm',
    'ACV-15 25mm': 'ACV 25mm',
    # APCs
    'AAVP-7A1': 'AAVP',
    'BTR-80': 'BTR-80',
    'BTR-82A': 'BTR-82A',
    'BTR-D Kord APC': 'BTR-D Kord',
    'BTR-MDM PKT RWS APC': 'BTR-MDM',
    'FV432 RWS': 'Bulldog RWS',
    'LAV III C6 RWS': 'LAV C6',
    'LAV III M2 RWS': 'LAV',
    'LAV-25': 'LAV',
    'M1126 CROWS M2': 'Stryker',
    'M1126 CROWS M240': 'Stryker M240',
    'M113A3 TLAV': 'TLAV',
    'MT-LB PKT': 'MT-LB PKT',
    'MT-LB VMK': 'MT-LB VMK',
    'MT-LBM 6MA S8': 'MT-LBM 6MA',
    'MT-LBM 6MA': 'MT-LBM 6MA',
    'ZSD05 APC': 'ZSD05',
    'ZSD05': 'ZSD05',
    'ZSL10 APC': 'ZSL10',
    'ZSL10': 'ZSL10',
    'PARS III M2 RWS': 'PARS M2',
    'PARS III MG3 RWS': 'PARS MG3',
    'PARS III Mk19 RWS': 'PARS Mk19',
    'ACV-15 M2': 'ACV M2',
    'ACV-15 MG3': 'ACV MG3',
    # AAs
    'BMP-1 ZU-23-2': 'BMP-1 ZU',
    'BTR-ZD Anti-Air': 'BTR-ZD ZU',
    'Modern Technical ZU-23-2': 'Techi ZU',
    'MT-LB ZU-23-2': 'MT-LB ZU',
    'Technical ZU-23-2': 'Techi ZU',
    'Ural-375D ZU-23-2': 'Ural ZU',
    # TOWs
    'BRDM-2 Spandrel': 'BRDM Spandrel',
    'CSK131 HJ8': 'CSK131 HJ8 (TOW)',
    'M-ATV TOW': 'MRAP TOW',
    'Simir Kornet': 'Simir Kornet',
    'Technical BMP-1': 'Techi BMP-1',
    # Other
    'FV107': 'Scimitar',
    'BRDM-2 S8': 'BRDM',
    'BRDM-2': 'BRDM',
    'ZTD05 MGS': 'ZTD05',
    'Sprut-SDM1 MGS': 'Sprut',
    # CROW/RWS cars
    'CSK131 QJC88 RWS': 'RWS',
    'LPPV RWS': 'RWS',
    'M-ATV CROWS M2': 'CROW',
    'M-ATV CROWS M240': 'CROW M240',
    'PMV RWS M2': 'RWS',
    'Tigr-M RWS Kord': 'RWS',
    'Cobra II MG3 RWS': 'RWS MG3',
    'Cobra II M2 RWS': 'RWS',
}


layers_data = {}


class SquadLayersTask(CrontabDiscordTask):
    URL = 'https://raw.githubusercontent.com/Squad-Wiki/squad-wiki-pipeline-map-data/master/completed_output/_Current%20Version/finished.json'
    crontab = '0 * * * *'
    run_on_start = True

    async def work(self):
        global layers_data
        layers = await self._get_layers_data()
        layers_data = layers

    async def _get_layers_data(self) -> dict:
        raw_data = await self._fetch_data()
        layers = self._extract_data(raw_data)
        return layers

    async def _fetch_data(self) -> dict:
        logger.info('Fetching data')
        res = await requests.session.get(self.URL)
        res.raise_for_status()
        data = json.loads(await res.text())
        return data

    def _extract_data(self, raw_data: dict) -> dict:
        layers = {}
        for layer in raw_data.get('Maps', []):
            layers[layer['Name']] = {
                'name': layer['Name'],
                'team1': self._parse_team(layer['team1']),
                'team2': self._parse_team(layer['team2']),
            }
        return layers

    @staticmethod
    def _parse_team(team_data: dict) -> dict:
        faction = FACTION_LOOKUP[team_data['faction']]
        vehicles = {
            VEHICLES_LOOKUP[vic['type']]
            for vic in team_data.get('vehicles', [])
            if vic['type'] in VEHICLES_LOOKUP
        }
        return {'faction': faction, 'vehicles': sorted(vehicles)}
