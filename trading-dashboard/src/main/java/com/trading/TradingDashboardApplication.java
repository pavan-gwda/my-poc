package com.trading;

import com.trading.config.TradingProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@EnableConfigurationProperties(TradingProperties.class)
public class TradingDashboardApplication {

    public static void main(String[] args) {
        SpringApplication.run(TradingDashboardApplication.class, args);
    }
}
