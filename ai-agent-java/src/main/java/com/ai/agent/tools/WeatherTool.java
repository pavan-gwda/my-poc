package com.ai.agent.tools;

import dev.langchain4j.agent.tool.Tool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Random;

/**
 * Weather tool for the AI agent.
 *
 * In production, this would call a real weather API like:
 * - OpenWeatherMap
 * - WeatherAPI
 * - AccuWeather
 *
 * For learning, we simulate responses.
 */
@Component
public class WeatherTool {

    private static final Logger log = LoggerFactory.getLogger(WeatherTool.class);
    private final Random random = new Random();

    // Simulated weather data for cities
    private static final Map<String, int[]> CITY_TEMPS = Map.of(
            "new york", new int[]{-5, 35},
            "london", new int[]{2, 25},
            "tokyo", new int[]{5, 35},
            "sydney", new int[]{15, 40},
            "paris", new int[]{0, 30},
            "bangalore", new int[]{20, 35},
            "mumbai", new int[]{22, 38},
            "chennai", new int[]{25, 42}
    );

    private static final String[] CONDITIONS = {
            "Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Foggy", "Clear"
    };

    @Tool("Get the current weather for a city. Returns temperature in Celsius and conditions.")
    public String getCurrentWeather(String city) {
        log.info("TOOL CALLED: getCurrentWeather({})", city);

        String normalizedCity = city.toLowerCase().trim();
        int[] tempRange = CITY_TEMPS.getOrDefault(normalizedCity, new int[]{10, 30});

        int temperature = random.nextInt(tempRange[1] - tempRange[0]) + tempRange[0];
        String condition = CONDITIONS[random.nextInt(CONDITIONS.length)];
        int humidity = random.nextInt(40) + 40; // 40-80%

        return String.format(
                "Weather in %s: %d°C, %s, Humidity: %d%%",
                capitalize(city), temperature, condition, humidity
        );
    }

    @Tool("Get the weather forecast for the next few days in a city.")
    public String getWeatherForecast(String city, int days) {
        log.info("TOOL CALLED: getWeatherForecast({}, {} days)", city, days);

        if (days > 7) days = 7;
        if (days < 1) days = 1;

        StringBuilder forecast = new StringBuilder();
        forecast.append(String.format("Weather forecast for %s:\n", capitalize(city)));

        String normalizedCity = city.toLowerCase().trim();
        int[] tempRange = CITY_TEMPS.getOrDefault(normalizedCity, new int[]{10, 30});

        for (int i = 1; i <= days; i++) {
            int high = random.nextInt(tempRange[1] - tempRange[0]) + tempRange[0];
            int low = high - random.nextInt(10) - 5;
            String condition = CONDITIONS[random.nextInt(CONDITIONS.length)];

            forecast.append(String.format("  Day %d: High %d°C, Low %d°C, %s\n",
                    i, high, low, condition));
        }

        return forecast.toString();
    }

    private String capitalize(String str) {
        if (str == null || str.isEmpty()) return str;
        return str.substring(0, 1).toUpperCase() + str.substring(1).toLowerCase();
    }
}
