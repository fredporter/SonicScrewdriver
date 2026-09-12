import json

import pytest
from pydantic import ValidationError

from sonic.cli import cli
from sonic.lib.catalog import Capacity, DeviceModel, load_catalog


def test_all_seeds_quarantined():
    items = load_catalog()
    assert len(items) == 21
    for item in items.values():
        assert item.flash_eligible is False
        assert item.provenance.verification == 'unverified'
        assert item.ram is None and item.storage is None
        assert item.legacy_claims


@pytest.mark.parametrize('payload', [{'value':-1,'unit':'bytes'}, {'value':16,'unit':'GB'}, {'value':True,'unit':'bytes'}])
def test_invalid_capacity(payload):
    with pytest.raises(ValidationError):
        Capacity.model_validate(payload)


def test_invalid_model_and_flash_eligibility():
    data=next(iter(load_catalog().values())).model_dump()
    for updates in [{'id':'../escape'}, {'flash_eligible':True}, {'unexpected':1}]:
        with pytest.raises(ValidationError):
            DeviceModel.model_validate({**data,**updates})


def test_duplicate_id_rejected(tmp_path):
    import yaml
    data=next(iter(load_catalog().values())).model_dump()
    (tmp_path/'bad.yaml').write_text(yaml.safe_dump({'schema_version':1,'devices':[data,data]}))
    with pytest.raises(ValueError,match='Duplicate'):
        load_catalog(tmp_path)


def test_offline_cli_no_state(tmp_path,monkeypatch,runner):
    monkeypatch.setenv('UDOS_HOME',str(tmp_path/'state'))
    result=runner.invoke(cli,['library','search','archer','--json'])
    assert result.exit_code==0
    assert len(json.loads(result.output)['devices'])==3
    assert '\x1b' not in result.output
    assert not (tmp_path/'state').exists()
    result=runner.invoke(cli,['library','show','missing'])
    assert result.exit_code!=0
