import pandas as pd
import os
from demoparser2 import DemoParser

DEMO_PATH = r"F:\steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\match730_003784108645122310500_1981615639_411.dem"
CSV_OUTPUT = "player_positions.csv"
TICK_RATE = 64

def main():
    if not os.path.exists(DEMO_PATH):
        print(f"Error: File {DEMO_PATH} not found.")
        return

    print(f"Parsing demo: {os.path.basename(DEMO_PATH)}...")
    parser = DemoParser(DEMO_PATH)
    
    print("Parsing player positions and view angles...")
    tick_df = parser.parse_ticks(["X", "Y", "Z", "pitch", "yaw", "team_num", "name", "is_alive"])
    tick_df = pd.DataFrame(tick_df)
    
    print("Parsing game state...")
    game_state_df = parser.parse_ticks(["is_freeze_period", "is_warmup_period", "is_terrorist_timeout", "is_ct_timeout", "is_technical_timeout", "is_waiting_for_resume"])
    game_state_df = pd.DataFrame(game_state_df)
    
    print("Filtering out non-active gameplay (warmup, freeze, timeouts)...")
    active_ticks = game_state_df[
        (game_state_df['is_freeze_period'] == False) &
        (game_state_df['is_warmup_period'] == False) &
        (game_state_df['is_terrorist_timeout'] == False) &
        (game_state_df['is_ct_timeout'] == False) &
        (game_state_df['is_technical_timeout'] == False) &
        (game_state_df['is_waiting_for_resume'] == False)
    ]['tick'].unique()
    
    print(f"Active ticks: {len(active_ticks)} out of {len(game_state_df['tick'].unique())}")
    
    tick_df = tick_df[tick_df['tick'].isin(active_ticks)].copy()
    
    print("Parsing weapon fire events...")
    fires_df = pd.DataFrame(parser.parse_event("weapon_fire"))
    
    if len(fires_df) > 0:
        fires_df['user_steamid'] = fires_df['user_steamid'].astype(str)
        fires_df['is_gun_fire'] = ~fires_df['weapon'].str.contains('knife', case=False, na=False)
        gun_fires = fires_df[fires_df['is_gun_fire'] == True][['tick', 'user_steamid']].copy()
        gun_fires['is_firing'] = True
    else:
        gun_fires = pd.DataFrame(columns=['tick', 'user_steamid', 'is_firing'])
    
    tick_df['steamid_str'] = tick_df['steamid'].astype(str)
    
    tick_df = tick_df.merge(
        gun_fires,
        left_on=['tick', 'steamid_str'],
        right_on=['tick', 'user_steamid'],
        how='left'
    )
    
    tick_df['is_firing'] = tick_df['is_firing'].fillna(False)
    
    tick_df['time_seconds'] = (tick_df['tick'] / TICK_RATE).round(2)
    
    output_df = tick_df[['tick', 'time_seconds', 'steamid', 'name', 'team_num', 'X', 'Y', 'Z', 'pitch', 'yaw', 'is_alive', 'is_firing']].copy()
    output_df = output_df.sort_values(['tick', 'steamid']).reset_index(drop=True)
    
    output_df.to_csv(CSV_OUTPUT, index=False)
    
    print(f"\nSaved {len(output_df)} rows to {CSV_OUTPUT}")
    print(f"\nSample data:")
    print(output_df.head(20))
    
    print(f"\nData summary:")
    print(f"  Unique players: {output_df['steamid'].nunique()}")
    print(f"  Team 2 (T): {len(output_df[output_df['team_num'] == 2])} rows")
    print(f"  Team 3 (CT): {len(output_df[output_df['team_num'] == 3])} rows")
    print(f"  Total firing events: {output_df['is_firing'].sum()}")
    print(f"  X range: {output_df['X'].min():.2f} to {output_df['X'].max():.2f}")
    print(f"  Y range: {output_df['Y'].min():.2f} to {output_df['Y'].max():.2f}")
    print(f"  Z range: {output_df['Z'].min():.2f} to {output_df['Z'].max():.2f}")
    print(f"  Pitch range: {output_df['pitch'].min():.2f} to {output_df['pitch'].max():.2f}")
    print(f"  Yaw range: {output_df['yaw'].min():.2f} to {output_df['yaw'].max():.2f}")

if __name__ == "__main__":
    main()