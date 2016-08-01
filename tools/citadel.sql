-- MySQL dump 10.13  Distrib 5.7.13, for osx10.11 (x86_64)
--
-- Host: localhost    Database: citadel
-- ------------------------------------------------------
-- Server version	5.7.13

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `citadel`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `citadel` /*!40100 DEFAULT CHARACTER SET utf8 */;

USE `citadel`;

--
-- Table structure for table `app`
--

DROP TABLE IF EXISTS `app`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `app` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `name` char(64) NOT NULL,
  `git` varchar(255) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `app`
--

LOCK TABLES `app` WRITE;
/*!40000 ALTER TABLE `app` DISABLE KEYS */;
INSERT INTO `app` VALUES (1,'2016-07-21 16:10:33','2016-07-21 16:10:33','test-ci','git@gitlab.ricebook.net:tonic/ci-test.git',0),(2,'2016-07-21 17:17:01','2016-07-21 17:17:01','erulb','git@gitlab.ricebook.net:tonic/pathlb.git',0);
/*!40000 ALTER TABLE `app` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `app_user_relation`
--

DROP TABLE IF EXISTS `app_user_relation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `app_user_relation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `appname` varchar(255) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`,`appname`),
  KEY `ix_app_user_relation_appname` (`appname`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `app_user_relation`
--

LOCK TABLES `app_user_relation` WRITE;
/*!40000 ALTER TABLE `app_user_relation` DISABLE KEYS */;
INSERT INTO `app_user_relation` VALUES (1,'2016-07-21 16:30:10','2016-07-21 16:30:10','test-ci',10056);
/*!40000 ALTER TABLE `app_user_relation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `container`
--

DROP TABLE IF EXISTS `container`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `container` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `appname` char(64) NOT NULL,
  `sha` char(64) NOT NULL,
  `container_id` char(64) NOT NULL,
  `entrypoint` varchar(50) NOT NULL,
  `env` varchar(50) NOT NULL,
  `cpu_quota` decimal(12,3) NOT NULL,
  `podname` varchar(50) NOT NULL,
  `nodename` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_container_container_id` (`container_id`),
  KEY `appname_sha` (`appname`,`sha`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `container`
--

LOCK TABLES `container` WRITE;
/*!40000 ALTER TABLE `container` DISABLE KEYS */;
/*!40000 ALTER TABLE `container` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `elb`
--

DROP TABLE IF EXISTS `elb`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `elb` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `addr` varchar(255) NOT NULL,
  `user_id` int(11) NOT NULL,
  `container_id` varchar(64) NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  `comment` text,
  PRIMARY KEY (`id`),
  KEY `ix_elb_user_id` (`user_id`),
  KEY `ix_elb_container_id` (`container_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `elb`
--

LOCK TABLES `elb` WRITE;
/*!40000 ALTER TABLE `elb` DISABLE KEYS */;
/*!40000 ALTER TABLE `elb` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `elb_route`
--

DROP TABLE IF EXISTS `elb_route`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `elb_route` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `elbname` varchar(64) DEFAULT NULL,
  `appname` varchar(255) DEFAULT NULL,
  `entrypoint` varchar(255) DEFAULT NULL,
  `podname` varchar(255) DEFAULT NULL,
  `domain` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_elb_route_appname` (`appname`),
  KEY `ix_elb_route_elbname` (`elbname`),
  KEY `ix_elb_route_entrypoint` (`entrypoint`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `elb_route`
--

LOCK TABLES `elb_route` WRITE;
/*!40000 ALTER TABLE `elb_route` DISABLE KEYS */;
/*!40000 ALTER TABLE `elb_route` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `release`
--

DROP TABLE IF EXISTS `release`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `release` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `sha` char(64) NOT NULL,
  `app_id` int(11) NOT NULL,
  `image` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `app_id` (`app_id`,`sha`),
  KEY `ix_release_sha` (`sha`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `release`
--

LOCK TABLES `release` WRITE;
/*!40000 ALTER TABLE `release` DISABLE KEYS */;
INSERT INTO `release` VALUES (1,'2016-07-21 16:10:33','2016-07-21 16:21:49','77eff496b58a94e7ef9289a4e943559d9bf05e91',1,'hub.ricebook.net/test-ci:77eff49'),(2,'2016-07-21 17:17:02','2016-07-21 17:17:02','22f8c0807b44e22cb5acd9446d467addd7601040',2,'hub.ricebook.net/erulb:22f8c08'),(3,'2016-07-22 13:59:53','2016-07-22 14:01:08','5a3d96f5a7b4ce131af4aec33b9c5f5523a6761d',1,'hub.ricebook.net/test-ci:5a3d96f'),(4,'2016-07-22 14:36:31','2016-07-22 14:36:31','e2b4a9e284834a15b14c156d238c6e9b6c718454',2,'hub.ricebook.net/erulb:e2b4a9e'),(5,'2016-07-22 16:42:43','2016-07-22 16:43:17','1397a3ffc49778305047b87781f6e632384251ff',1,'hub.ricebook.net/test-ci:1397a3f'),(6,'2016-08-01 15:31:36','2016-08-01 15:33:36','63cdb03fa1fa31efa2d16820b33ca52dbfe8780f',1,'hub.ricebook.net/test-ci:63cdb03');
/*!40000 ALTER TABLE `release` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `special_elb_route`
--

DROP TABLE IF EXISTS `special_elb_route`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `special_elb_route` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `ip` varchar(16) DEFAULT NULL,
  `domain` varchar(255) DEFAULT NULL,
  `elbname` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_special_elb_route_ip` (`ip`),
  KEY `ix_special_elb_route_domain` (`domain`),
  KEY `ix_special_elb_route_elbname` (`elbname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `special_elb_route`
--

LOCK TABLES `special_elb_route` WRITE;
/*!40000 ALTER TABLE `special_elb_route` DISABLE KEYS */;
/*!40000 ALTER TABLE `special_elb_route` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-08-01 18:02:37
