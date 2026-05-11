from __future__ import annotations

import json

import psycopg

from app.config import settings


def psycopg_url() -> str:
    return settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")


TOOLS: list[dict] = [
    {
        "slug": "wttr_in",
        "name": "Weather",
        "description": "Current weather for any location in JSON format.",
        "category": "weather",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "https://wttr.in/{location}?format=j1",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "wttr_in",
            "description": "Get current weather data for a location. Returns temperature, humidity, wind, and conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. Sao Paulo, London, New York",
                    }
                },
                "required": ["location"],
            },
        },
        "prompt_block": "[wttr_in] Use this tool to check the current weather for any city. Provide the city name as `location`.",
    },
    {
        "slug": "ip_api",
        "name": "IP Geolocation",
        "description": "Geolocation data for a given IP address.",
        "category": "geolocation",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "http://ip-api.com/json/{ip}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "ip_api",
            "description": "Get geolocation data (country, city, lat/lon, ISP) for an IP address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP address to look up, e.g. 8.8.8.8",
                    }
                },
                "required": ["ip"],
            },
        },
        "prompt_block": "[ip_api] Use this tool when the user provides an IP address and you need country/city/ISP information.",
    },
    {
        "slug": "rest_countries",
        "name": "Country Info",
        "description": "Detailed data about countries: population, capital, currency, flag, languages.",
        "category": "reference",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "https://restcountries.com/v3.1/name/{name}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "rest_countries",
            "description": "Get detailed information about a country including population, capital, currency, languages, and flag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Country name in English, e.g. Brazil, Japan, Germany",
                    }
                },
                "required": ["name"],
            },
        },
        "prompt_block": "[rest_countries] Use this tool when the user asks for country facts (population, capital, currency, flag, languages).",
    },
    {
        "slug": "open_library",
        "name": "Book Search",
        "description": "Search books by title, author, or ISBN via Open Library.",
        "category": "reference",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "https://openlibrary.org/search.json?q={query}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "open_library",
            "description": "Search for books by title, author, or subject via Open Library.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'the lord of the rings', 'asimov foundation'",
                    }
                },
                "required": ["query"],
            },
        },
        "prompt_block": "[open_library] Use this tool to search books by title, author, or subject when the user asks about literature.",
    },
    {
        "slug": "universities_api",
        "name": "Universities",
        "description": "List universities by country.",
        "category": "reference",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "http://universities.hipolabs.com/search?country={country}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "universities_api",
            "description": "Get a list of universities and colleges in a given country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "Country name in English, e.g. Brazil, United States, Japan",
                    }
                },
                "required": ["country"],
            },
        },
        "prompt_block": "[universities_api] Use this tool when the user asks which universities exist in a given country.",
    },
    {
        "slug": "jsonplaceholder",
        "name": "JSONPlaceholder",
        "description": "Fake API for testing: posts, comments, users, todos.",
        "category": "testing",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "https://jsonplaceholder.typicode.com/{resource}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "jsonplaceholder",
            "description": "Fetch fake test data from JSONPlaceholder. Resources: posts, comments, users, todos, albums.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource path with optional ID, e.g. posts/1, posts, comments, users, todos",
                    }
                },
                "required": ["resource"],
            },
        },
        "prompt_block": "[jsonplaceholder] Use this tool to fetch sample REST data (posts, comments, users, todos) for testing or examples.",
    },
    {
        "slug": "pokeapi",
        "name": "PokeAPI",
        "description": "Pokemon data: stats, types, abilities, evolution chain.",
        "category": "entertainment",
        "executor": "web_fetch",
        "is_builtin": True,
        "method": "GET",
        "endpoint": "https://pokeapi.co/api/v2/pokemon/{pokemon}",
        "headers_template": {},
        "body_template": None,
        "variables_schema": [],
        "schema": {
            "name": "pokeapi",
            "description": "Get Pokemon data including stats, types, abilities, and sprites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pokemon": {
                        "type": "string",
                        "description": "Pokemon name or ID, e.g. ditto, pikachu, 25, 6",
                    }
                },
                "required": ["pokemon"],
            },
        },
        "prompt_block": "[pokeapi] Use this tool when the user asks about Pokemon stats, types, abilities, or sprites.",
    },
]


def main() -> None:
    with psycopg.connect(psycopg_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM tool_definitions
                WHERE slug = 'web_fetch'
                  AND NOT EXISTS (
                    SELECT 1 FROM agent_instance_tools ait WHERE ait.tool_id = tool_definitions.id
                  )
                """
            )
            for tool in TOOLS:
                cursor.execute(
                    """
                    INSERT INTO tool_definitions
                        (slug, name, description, category, prompt_block, schema, executor,
                         is_builtin, method, endpoint, headers_template, body_template, variables_schema)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        prompt_block = EXCLUDED.prompt_block,
                        schema = EXCLUDED.schema,
                        executor = EXCLUDED.executor,
                        is_builtin = EXCLUDED.is_builtin,
                        method = EXCLUDED.method,
                        endpoint = EXCLUDED.endpoint,
                        headers_template = EXCLUDED.headers_template,
                        body_template = EXCLUDED.body_template,
                        variables_schema = EXCLUDED.variables_schema
                    """,
                    (
                        tool["slug"],
                        tool["name"],
                        tool["description"],
                        tool["category"],
                        tool["prompt_block"],
                        json.dumps(tool["schema"]),
                        tool["executor"],
                        tool["is_builtin"],
                        tool["method"],
                        tool["endpoint"],
                        json.dumps(tool["headers_template"]),
                        tool["body_template"],
                        json.dumps(tool["variables_schema"]),
                    ),
                )
            print(f"Seeded {len(TOOLS)} built-in tool definitions.")


if __name__ == "__main__":
    main()
