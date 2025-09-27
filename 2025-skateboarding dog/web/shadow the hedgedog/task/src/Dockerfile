FROM eclipse-temurin:24-jdk-alpine AS build

WORKDIR /app

COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

RUN ./mvnw dependency:go-offline -B

COPY src ./src

RUN ./mvnw clean package -DskipTests

FROM eclipse-temurin:24-jdk-alpine
WORKDIR /app

COPY --from=build /app/target/shadow-the-hedgedog-0.0.1-SNAPSHOT.jar app.jar

ENV JWT_SECRET="redacted_redacted_redacted_redacted_redacted"
ENV FLAG="skbdg{redacted}"

EXPOSE 1337
ENTRYPOINT ["java","-jar","app.jar","--spring.profiles.active=prod"]
