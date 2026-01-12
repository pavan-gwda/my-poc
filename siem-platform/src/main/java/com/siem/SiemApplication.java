package com.siem;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.kafka.annotation.EnableKafkaStreams;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableKafkaStreams
@EnableScheduling
@ConfigurationPropertiesScan
public class SiemApplication {

    public static void main(String[] args) {
        SpringApplication.run(SiemApplication.class, args);
    }
}
