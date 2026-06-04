#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive player search to find SofaScore player ID."""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

def search_and_display_player(player_name: str):
    """Search for player and display all results."""
    driver = None
    try:
        print(f"\nSearching for '{player_name}'...")
        driver = webdriver.Edge()

        # Open search page
        search_url = f"https://www.sofascore.com/search?q={player_name.replace(' ', '+')}"
        driver.get(search_url)

        # Wait for results to load
        time.sleep(3)

        # Extract player data from page using JavaScript
        script = """
        var players = [];
        document.querySelectorAll('[data-testid*="player"], a[href*="/player/"]').forEach(el => {
            var link = el.href || el.closest('a')?.href;
            var text = el.textContent || el.innerText;
            if (link && link.includes('/player/')) {
                var match = link.match(/\\/player\\/([^\\/]+)\\/(\\d+)/);
                if (match) {
                    players.push({
                        name: text.trim(),
                        slug: match[1],
                        id: parseInt(match[2]),
                        url: link
                    });
                }
            }
        });

        // Remove duplicates
        var seen = new Set();
        return players.filter(p => {
            var key = p.id;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
        """

        results = driver.execute_script(script)

        if results:
            print(f"\nFound {len(results)} players:\n")
            for i, player in enumerate(results, 1):
                print(f"{i}. {player['name']:40} (ID: {player['id']:8})")
                print(f"   URL: {player['url']}\n")

            return results
        else:
            print("No players found. Try a different search term.")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    # Search for Alex Bruno
    results = search_and_display_player("Alex Bruno")

    if results:
        print("\n" + "="*80)
        print("To extract this player's career data, use:")
        print("")
        player_id = results[0]['id']
        print(f'  python -c "from extract_player_career_dom import extract_by_id; extract_by_id({player_id}, \'Alex Bruno\')"')
        print("="*80)
