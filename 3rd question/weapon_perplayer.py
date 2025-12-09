import pandas as pd
import os
from demoparser2 import DemoParser

BASE_PATH = r"F:\steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays"

DEMOS_AND_PLAYERS = [
    ("match730_003784446263911514537_1478082598_187.dem", 76561198262157518, "arckay."),
    ("match730_003784108645122310500_1981615639_411.dem", 76561198155980865, "KosyaK"),
    ("match730_003783868685299483229_2047292477_192.dem", 76561198962223770, "patsan"),
    ("match730_003788960304604381265_2009075138_192.dem", 76561198155980865, "KosyaK"),
    ("match730_003788558291370508879_1730936726_187.dem", 76561198155980865, "KosyaK"),
    ("match730_003790222312024835007_0827502415_272.dem", 76561198816184658, "Unknown"),
    ("match730_003790275752155414789_0281693499_411.dem", 76561198816184658, "Unknown"),
    ("match730_003790277747167723523_2066055668_187.dem", 76561198816184658, "Unknown"),
    ("match730_003790301240638832694_0587072542_186.dem", 76561198816184658, "Unknown"),
]

CSV_OUTPUT = "weapon_usage_per_player.csv"

TRACKED_STEAMIDS = set([76561198262157518, 76561198155980865, 76561198962223770, 76561198816184658])

def normalize_weapon_name(weapon_name):
    if pd.isna(weapon_name) or weapon_name == '':
        return 'Unknown'
    
    weapon_str = str(weapon_name).lower()
    
    if 'knife' in weapon_str and weapon_str not in ['weapon_knife', 'weapon_knife_t', 'knife', 'knife_t']:
        if 'kukri' in weapon_str:
            return 'Kukri Knife'
        elif '_t' in weapon_str or 'bayonet' in weapon_str or 'karambit' in weapon_str:
            return 'knife_t'
        return 'knife'
    
    mapping = {
        'weapon_ak47': 'AK-47',
        'ak47': 'AK-47',
        'weapon_m4a1': 'M4A4',
        'm4a1': 'M4A4',
        'weapon_m4a1_silencer': 'M4A1-S',
        'm4a1_silencer': 'M4A1-S',
        'weapon_awp': 'AWP',
        'awp': 'AWP',
        'weapon_deagle': 'Desert Eagle',
        'deagle': 'Desert Eagle',
        'weapon_glock': 'Glock-18',
        'glock': 'Glock-18',
        'weapon_usp_silencer': 'USP-S',
        'usp_silencer': 'USP-S',
        'weapon_hkp2000': 'P2000',
        'hkp2000': 'P2000',
        'weapon_elite': 'Dual Berettas',
        'elite': 'Dual Berettas',
        'weapon_p250': 'P250',
        'p250': 'P250',
        'weapon_tec9': 'Tec-9',
        'tec9': 'Tec-9',
        'weapon_fiveseven': 'Five-SeveN',
        'fiveseven': 'Five-SeveN',
        'weapon_cz75a': 'CZ75-Auto',
        'cz75a': 'CZ75-Auto',
        'weapon_revolver': 'R8 Revolver',
        'revolver': 'R8 Revolver',
        'weapon_nova': 'Nova',
        'nova': 'Nova',
        'weapon_xm1014': 'XM1014',
        'xm1014': 'XM1014',
        'weapon_mag7': 'MAG-7',
        'mag7': 'MAG-7',
        'weapon_sawedoff': 'Sawed-Off',
        'sawedoff': 'Sawed-Off',
        'weapon_m249': 'M249',
        'm249': 'M249',
        'weapon_negev': 'Negev',
        'negev': 'Negev',
        'weapon_mac10': 'MAC-10',
        'mac10': 'MAC-10',
        'weapon_mp9': 'MP9',
        'mp9': 'MP9',
        'weapon_mp7': 'MP7',
        'mp7': 'MP7',
        'weapon_ump45': 'UMP-45',
        'ump45': 'UMP-45',
        'weapon_p90': 'P90',
        'p90': 'P90',
        'weapon_bizon': 'PP-Bizon',
        'bizon': 'PP-Bizon',
        'weapon_mp5sd': 'MP5-SD',
        'mp5sd': 'MP5-SD',
        'weapon_famas': 'FAMAS',
        'famas': 'FAMAS',
        'weapon_galilar': 'Galil AR',
        'galilar': 'Galil AR',
        'weapon_aug': 'AUG',
        'aug': 'AUG',
        'weapon_sg556': 'SG 553',
        'sg556': 'SG 553',
        'weapon_ssg08': 'SSG 08',
        'ssg08': 'SSG 08',
        'weapon_scar20': 'SCAR-20',
        'scar20': 'SCAR-20',
        'weapon_g3sg1': 'G3SG1',
        'g3sg1': 'G3SG1',
        'weapon_hegrenade': 'High Explosive Grenade',
        'hegrenade': 'High Explosive Grenade',
        'weapon_flashbang': 'Flashbang',
        'flashbang': 'Flashbang',
        'weapon_smokegrenade': 'Smoke Grenade',
        'smokegrenade': 'Smoke Grenade',
        'weapon_incgrenade': 'Incendiary Grenade',
        'incgrenade': 'Incendiary Grenade',
        'inferno': 'Incendiary Grenade',
        'weapon_molotov': 'Molotov',
        'molotov': 'Molotov',
        'weapon_decoy': 'Decoy Grenade',
        'decoy': 'Decoy Grenade',
        'weapon_knife': 'knife',
        'knife': 'knife',
        'weapon_knife_t': 'knife_t',
        'knife_t': 'knife_t',
        'weapon_c4': 'C4 Explosive',
        'c4': 'C4 Explosive',
        'weapon_taser': 'Zeus x27',
        'taser': 'Zeus x27',
    }
    
    return mapping.get(weapon_str, weapon_name)

def main():
    all_player_weapon_data = []
    
    for demo_file, steamid, player_name in DEMOS_AND_PLAYERS:
        demo_path = os.path.join(BASE_PATH, demo_file)
        
        if not os.path.exists(demo_path):
            print(f"Warning: {demo_file} not found, skipping...")
            continue
        
        print(f"\nProcessing {demo_file}...")
        
        try:
            parser = DemoParser(demo_path)
            
            tick_df = parser.parse_ticks(["active_weapon_name", "is_alive", "name"])
            tick_df = pd.DataFrame(tick_df)
            
            print(f"  Parsing weapon fires and hits...")
            fires_df = pd.DataFrame(parser.parse_event("weapon_fire"))
            hurts_df = pd.DataFrame(parser.parse_event("player_hurt"))
            
            if len(fires_df) > 0:
                fires_df['user_steamid'] = fires_df['user_steamid'].astype(str)
                fires_df['weapon'] = fires_df['weapon'].apply(normalize_weapon_name)
                sample_fire_weapons = fires_df['weapon'].unique()[:5]
                print(f"  Sample weapon_fire names (normalized): {sample_fire_weapons}")
            
            if len(hurts_df) > 0:
                hurts_df['attacker_steamid'] = hurts_df['attacker_steamid'].astype(str)
                hurts_df['weapon'] = hurts_df['weapon'].apply(normalize_weapon_name)
                sample_hurt_weapons = hurts_df['weapon'].unique()[:5]
                print(f"  Sample player_hurt weapon names (normalized): {sample_hurt_weapons}")
            
            all_steamids = tick_df['steamid'].unique()
            
            print(f"  Found {len(all_steamids)} unique players")
            tracked_in_demo = [sid for sid in all_steamids if sid in TRACKED_STEAMIDS]
            if tracked_in_demo:
                print(f"  Tracked players in this demo: {tracked_in_demo}")
            
            for current_steamid in all_steamids:
                current_steamid_str = str(current_steamid)
                player_df = tick_df[
                    (tick_df['steamid'] == current_steamid) & 
                    (tick_df['is_alive'] == True) &
                    (tick_df['active_weapon_name'].notna())
                ].copy()
                
                if len(player_df) == 0:
                    continue
                
                player_actual_name = player_df['name'].iloc[0]
                
                player_fires = fires_df[fires_df['user_steamid'] == current_steamid_str].copy()
                player_hits = hurts_df[hurts_df['attacker_steamid'] == current_steamid_str].copy()
                
                if current_steamid in TRACKED_STEAMIDS:
                    print(f"    DEBUG: Player {player_actual_name} (ID: {current_steamid})")
                    print(f"           Total fires in events: {len(player_fires)}, Total hits: {len(player_hits)}")
                    if len(player_fires) > 0:
                        print(f"           Fire weapons: {player_fires['weapon'].unique()[:5]}")
                    if len(player_hits) > 0:
                        print(f"           Hit weapons: {player_hits['weapon'].unique()[:5]}")


                
                weapon_stats = {}
                
                for weapon in player_df['active_weapon_name'].unique():
                    ticks_held = len(player_df[player_df['active_weapon_name'] == weapon])
                    
                    shots_fired = len(player_fires[player_fires['weapon'] == weapon])
                    shots_hit = len(player_hits[player_hits['weapon'] == weapon])
                    
                    accuracy = (shots_hit / shots_fired * 100) if shots_fired > 0 else 0.0
                    
                    weapon_stats[weapon] = {
                        'ticks_held': ticks_held,
                        'shots_fired': shots_fired,
                        'shots_hit': shots_hit,
                        'accuracy_percentage': round(accuracy, 2)
                    }
                
                weapon_data = pd.DataFrame.from_dict(weapon_stats, orient='index').reset_index()
                weapon_data.columns = ['weapon', 'ticks_held', 'shots_fired', 'shots_hit', 'accuracy_percentage']
                
                weapon_data['steamid'] = current_steamid
                weapon_data['player_name'] = player_actual_name
                weapon_data['is_tracked'] = current_steamid in TRACKED_STEAMIDS
                weapon_data['demo'] = demo_file
                
                all_player_weapon_data.append(weapon_data)
            
            print(f"  Processed {len(all_steamids)} players")
            
        except Exception as e:
            print(f"  Error processing {demo_file}: {e}")
            continue
    
    if not all_player_weapon_data:
        print("\nNo weapon data collected!")
        return
    
    combined_df = pd.concat(all_player_weapon_data, ignore_index=True)
    
    aggregated = combined_df.groupby(['steamid', 'player_name', 'is_tracked', 'weapon']).agg(
        total_ticks_held=('ticks_held', 'sum'),
        total_shots_fired=('shots_fired', 'sum'),
        total_shots_hit=('shots_hit', 'sum'),
        demos_appeared=('demo', 'count')
    ).reset_index()
    
    aggregated['accuracy_percentage'] = (
        (aggregated['total_shots_hit'] / aggregated['total_shots_fired']) * 100
    ).round(2)
    
    aggregated.loc[aggregated['total_shots_fired'] == 0, 'accuracy_percentage'] = 0.0
    
    aggregated['weapon_rank'] = aggregated.groupby('steamid')['total_ticks_held'].rank(method='dense', ascending=False).astype(int)
    
    aggregated = aggregated.sort_values(['is_tracked', 'steamid', 'weapon_rank'], ascending=[False, True, True])
    
    output_df = aggregated[['steamid', 'player_name', 'is_tracked', 'weapon_rank', 'weapon', 'total_ticks_held', 'total_shots_fired', 'total_shots_hit', 'accuracy_percentage', 'demos_appeared']]
    
    output_df.to_csv(CSV_OUTPUT, index=False)
    
    print(f"\n{'='*80}")
    print(f"Per-player weapon usage saved to {CSV_OUTPUT}")
    print(f"{'='*80}\n")
    
    tracked_players = output_df[output_df['is_tracked'] == True]['steamid'].nunique()
    other_players = output_df[output_df['is_tracked'] == False]['steamid'].nunique()
    
    print(f"Total tracked players: {tracked_players}")
    print(f"Total other players: {other_players}")
    print(f"Total rows: {len(output_df)}")
    
    print(f"\n{'='*80}")
    print("Sample - Tracked Players Top Weapons:")
    print(f"{'='*80}\n")
    tracked_sample = output_df[output_df['is_tracked'] == True].head(20)
    print(tracked_sample.to_string(index=False))
    
    print(f"\n{'='*80}")
    print("Sample - Other Players Top Weapons:")
    print(f"{'='*80}\n")
    other_sample = output_df[output_df['is_tracked'] == False].head(20)
    print(other_sample.to_string(index=False))

if __name__ == "__main__":
    main()